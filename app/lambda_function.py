import os
import json
import logging
import boto3
import requests
import urllib.parse
#from app.lib.lex_teams_adapter import LexTeamsAdapter, LexTeamsAdapterConfig
from lib.lex_teams_adapter import LexTeamsAdapter, LexTeamsAdapterConfig
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("<<lex-teams-adapter>> Initializing boto3 clients for SSM and Lex")

# Initialize boto3 client at global scope for connection reuse
lexClient = boto3.client('lex-runtime')
secmgrClient = boto3.client('secretsmanager')

# Initialize app at global scope for reuse across invocations
app = None

def get_secret():
    secret_name = os.environ['CONFIG']

    try:
        get_secret_value_response = secmgrClient.get_secret_value(
            SecretId=secret_name
        )
        return get_secret_value_response['SecretString']
    except ClientError as e:
        print("An error occurred:", e)
    


def lambda_handler(event, context):

    # Region Step 0: Initialization
    logger.info('lambda_handler: Lambda event = ' + json.dumps(event))
    config = LexTeamsAdapterConfig.from_json(get_secret())
    adapter = LexTeamsAdapter.from_json(config, event['body'])

    if adapter.type == 'conversationUpdate':
        return close(200, "message type conversationUpdate - ignored")

    # Step 1: Retrieve input values from MS Teams event
    userInputMessage = None
    try:
        body = json.loads(event['body'])
        logger.info('lambda_handler: request.body = ' +
                    json.dumps(body, indent=2, sort_keys=True))

        text = body['text']
        logger.info('lambda_handler: request.body.text = ' + text)

        conversation = body["conversation"]

        userName = body['from']['name']
        aadObjectId = body['from']['aadObjectId']

        teamsTeamId = None
        teamsChannelId = None
        if body.get('channelData', None):
            teamsTeamId = body['channelData'].get('teamsTeamId', None)
            teamsChannelId = body['channelData'].get('teamsChannelId', None)

        recipient = body["recipient"],
        replyToId = body["id"]
        logger.debug('lambda_handler: request.body.from.name = ' + userName)
        logger.debug(
            'lambda_handler: request.body.from.aadObjectId = ' + aadObjectId)

        returnUrl = body['serviceUrl'] + 'v3/conversations/' + \
            body['conversation']['id'] + '/activities/' + body['id']
        logger.debug('lambda_handler: returnUrl = ' + returnUrl)

        userInputMessage = text
        index = text.find('</at>')
        if index >= 0:
            userInputMessage = text[index+5:]
            if userInputMessage.endswith('\\n'):
                userInputMessage = userInputMessage[:len(userInputMessage)-2]
            userInputMessage = userInputMessage.strip()
            logger.info(
                'lambda_handler: request.body.text(userInputMessage) = ' + userInputMessage)

    except KeyError as e:
        logger.error(
            'Exception retrieving values from event: missing key = ' + str(e))

    if userInputMessage is None:
        logger.error(
            'lambda_handler: configuration error: unable to retrieve values from MS Teams input event')
        return close(400, "Sorry, there was missing information in the request I received. Looks like a gateway logic coding error.")

    # Step 2: Retrieve MS Teams app configuration information and valid MS tenant IDs
    try:
        msAppId = adapter.config.ms_app_id
        msAppPass = adapter.config.client_secret
        msTenantIds = adapter.config.valid_tenant_ids
        logger.info('lambda_handler: MSAppID=%s****%s, client_secret=%s****%s',
                    msAppId[:4], msAppId[-4:], msAppPass[:4], msAppPass[-4:])

    except Exception as e:
        logger.error('Exception retrieving MS App info: ' + str(e))
        logger.error(
            'lambda_handler: configuration error: unable to retrieve MS App ID and password parameter name environment variables.')
        return close(200, "Sorry, the API gateway is not configured with a Microsoft App ID and client secret.")

    # Step 3: verify MS Teams tenant ID(s)
    valid_tenant_found = False
    if (msTenantIds):
        for validTenant in msTenantIds.split(","):
            logger.info('lambda_handler: valid tenant id=%s***%s',
                        validTenant[:4], validTenant[-4:])
            if adapter.tenant_id == validTenant:
                valid_tenant_found = True
                break

    if not valid_tenant_found:
        logger.error(
            'lambda_handler: no valid MS tenant ID found in the input request.')
        errorMessage = "Sorry, you must be part of an authorized domain to use this application."
        message = {
            "type": "message",
            "from": recipient,
            "conversation": conversation,
            "recipient": adapter.receivedFrom,
            "text": errorMessage,
            "replyToId": replyToId
        }
        postResponseToTeams(message, returnUrl, msAppId, msAppPass)
        return close(401, errorMessage)

    # Step 4: Retrieve Lex bot configuration information
    lexBotName = os.environ.get('LEX_BOT_NAME', None)
    lexBotAlias = os.environ.get('LEX_BOT_ALIAS', None)
    if lexBotName is None or lexBotAlias is None:
        logger.error(
            'lambda_handler: configuration error: unable to retrieve Lex bot name and alias environment variables.')
        errorMessage = "Sorry, the API gateway is not configured with an Amazon Lex bot."
        message = {
            "type": "message",
            "from": recipient,
            "conversation": conversation,
            "recipient": adapter.receivedFrom,
            "text": errorMessage,
            "replyToId": replyToId
        }
        postResponseToTeams(message, returnUrl, msAppId, msAppPass)
        return close(200, errorMessage)

    # Step 5: Get existing Lex session attributes, if available
    try:
        response = lexClient.get_session(
            botName=lexBotName,
            botAlias=lexBotAlias,
            userId=aadObjectId
        )

        # get session attributes and remove any null values
        session_attributes = {
            k: v for k, v in response["sessionAttributes"].items() if v is not None}

    except Exception as e:
        # no session attributes available
        session_attributes = {}

    # make sure session attributes have MS teams data
    teamsAttributes = {
        'userName': userName,
        'firstName': userName.split(' ')[0],
        'aadObjectId': aadObjectId,
        'tenantId': adapter.tenant_id,
        'teamsTeamId': teamsTeamId,
        'teamsChannelId': teamsChannelId,
        'ms-teams-request-body': json.dumps(body)
    }
    for key in teamsAttributes:
        if teamsAttributes[key] is None:
            if key in session_attributes:
                del session_attributes[key]
        else:
            session_attributes[key] = teamsAttributes[key]
    logger.info('lambda_handler: session attributes = ' +
                json.dumps(session_attributes))

    # Step 6: Call the Lex bot
    try:
        logger.info(
            'lambda_handler: calling Lex post_text, inputText = ' + userInputMessage)
        response = lexClient.post_text(
            botName=lexBotName,
            botAlias=lexBotAlias,
            userId=aadObjectId,
            sessionAttributes=session_attributes,
            inputText=userInputMessage
        )

    except Exception as e:
        logger.error('Exception calling Lex post_text: ' + str(e))

    logger.info('lambda_handler: bot response = ' + json.dumps(response))
    responseMessage = response.get(
        'message', 'Sorry, there was no response from the Amazon Lex bot.')

    # Step 7: Build the response for MS Teams
    message = {
        "type": "message",
        "from": recipient,
        "conversation": conversation,
        "recipient": adapter.receivedFrom,
        "text": responseMessage,
        "replyToId": replyToId
    }

    # translate any Lex response card buttons to Teams format
    if 'responseCard' in response:
        try:
            # TODO - confirm the [0] here, i.e., only one genericAttachments for buttons and it is the zeroeth item
            lexButtons = response['responseCard']['genericAttachments'][0]['buttons']
            teamsButtons = {
                "attachmentLayout": "list",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.thumbnail",
                        "content": {
                            "buttons": [{"type": "imBack", "title": item["text"], "value": item["value"]} for item in lexButtons]
                        }
                    }
                ]
            }
            message.update(teamsButtons)
        except KeyError as e:
            logger.error(
                'Exception retrieving response card buttons from Lex response: ' + str(e))

        # Add image
        try:
            teamsButtons['attachments'][0]['content']['images'] = [{
                "url": response['responseCard']['genericAttachments'][0]['imageUrl'],
                "alt": response['responseCard']['genericAttachments'][0]['title']
            }]
            message.update(teamsButtons)
        except KeyError:
            pass
    # Step 8: Send the response to MS Teams
    postResponseToTeams(message, returnUrl, msAppId, msAppPass)

    return close(200, responseMessage)


def postResponseToTeams(message, returnUrl, msAppId, msAppPass):
    logger.info('postResponseToTeams: message = %s', message)
    logger.debug('postResponseToTeams: returnUrl = %s', returnUrl)

    # obtain authorization token
    hed = {"Host": "login.microsoftonline.com",
           "Content-Type": "application/x-www-form-urlencoded"}
    authUrl = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
    authMessage = "grant_type=client_credentials&client_id=" + msAppId + "&client_secret=" + \
        urllib.parse.quote(msAppPass, safe="") + \
        "&scope=https%3A%2F%2Fapi.botframework.com%2F.default"

    logger.debug(
        'postResponseToTeams: obtaining MS Bot Framework access token')
    r = requests.post(authUrl, data=authMessage, headers=hed)
    logger.debug(
        ' postResponseToTeams: MS Bot Framework POST status = ' + str(r.status_code))

    authReply = json.loads(r.text)
    logger.debug(
        'postResponseToTeams: MS Bot Framework access token = ' + json.dumps(authReply))

    hed = {"Authorization": "Bearer " +
           authReply["access_token"], "Content-Type": "application/json"}
    r = requests.post(returnUrl, data=json.dumps(message), headers=hed)
    logger.info(
        'postResponseToTeams: MS Bot Framework POST status = ' + str(r.status_code))

    return r.status_code


def close(status_code, message_text):
    return_value = {
        "statusCode": status_code,
        "body": json.dumps({
            "type": "message",
            "text": message_text
        })
    }

    return return_value

def parse_config(json_config):
    try:
        configuration = json.loads(json_config)

    except Exception as e:
        logger.error(
            "Encountered an error parsing config from SercretsManager: " + str(e))

    return configuration
