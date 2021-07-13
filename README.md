# Amazon Lex - Microsoft Teams integration.

**NOTE: I'm no longer actively working on this. The below was used just to test the integration.**

This project contains source code for integration [Amazon Lex](https://aws.amazon.com/lex/) with Microsoft Teams using 
[AWS Lambda](https://aws.amazon.com/lambda/). To deploy this project, you already need to have: 

- AWS Account
- Lex bot
- o365 subscription that includes MS Teams
- Azure AD

## Step 1: Get Tenant ID

Find tenant ID through the Azure portal

- Sign in to the Azure portal.
- Select Azure Active Directory.
- Select Properties.
- Then, scroll down to the Tenant ID field. Your tenant ID will be in the box.
  
## Step 2: Get MSAppID and MSAppClientSecret from Azure portal

- Open the [App registrations in your Azure portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
- Click **+ New registration**
- Name: (name)
- For Supported account types - **Who can use this application** or access this API?
  -	**Accounts in any organizational directory (Any Azure AD directory - Multitenant)**
- Click **Register**
- Select Manifest, and **note the appId value** for a future configuration step.
- Select **API permissions**, **Add a permission**, select the **Microsoft Graph category**, Application permissions, and add `User.Read.All`**.  
- Select **'Add permissions'**.
  - This permission allows the app to read data in your organization's directory about the signed in user.
- Under API permissions, **remove the permission** `User.Read (Delegated)`. 
- Select **Certificates & secrets**, and click **New client secret**
- Enter a Description such as `(name)-client-secret` and select Never for Expires.
- Click **Add**, and then **note the Value** for a future configuration step.
- Select Owners, and add any additional owners for the application.

## Step 3: Deploy Lambda function

Deploy the SAM template using [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) to get started. You can do so as follows:

```
sam build --use-container --cached
sam deploy --guided
```

You'll be asked for the following parameters:

| Variable         | Default Value           | Usage                                   |
|------------------|-------------------------|-----------------------------------------|
| LexBotName       | chatops                 | Name of the Lex bot to integrate with   |
| LexBotAlias      | dev                     | Alias for the Lex bot to integrate with |
| MSAppId          | xxx                     | Step 2                                  |
| MSAppClientSecret| xxx                     | Step 2                                  | 
| MSTenantID       | xxx                     | Step 1                                  | 

When the deployment is finished you will receive a `API Gateway endpoint URL for LexAdapter`. **Note this url, you need 
it in Step 4**.

## Step 4: Register the app with the Microsoft Bot Framework

- Navigate to [Microsoft botframework portal](https://dev.botframework.com/bots/new)
-	Set a **Display name**
-	Set a **Bot handle**
  -	L**ong description:** Self-service bot to help developers and support staff streamline operations
  -	**Messaging endpoint:** You got this from Step 3.
-	**Do NOT select Enable Streaming Endpoint**
-	For Paste your app ID below to continue, **paste the appId value from Step 2 above**.
-	Leave the other values as is, agree to the terms, and click Register.
-	On the Channels page, click the Microsoft Teams icon under Add a featured channel
-	Select Microsoft Teams Commercial (most common) and click Save.
-	Agree to the Terms of Service and click Agree

## Step 5: Add bot to Microsoft Teams

- Go to Microsoft Teams
- Under **Apps** select **App Studio**
- In the top menu, select **Manifest editor**
- Click **Create a new app**
- **Enter** a **Short name** and **Full name**
- App ID: click **Generate** to get an **App ID** for this bot (**this is different from the AppID from Step 3**)
- **Package name:** `vcc`
- **Version:** `1.0.0`
- **Short description:** Self-service bot to help developers and support staff streamline operations
- **Full description:** This bot allows users to obtain information about cloud accounts connections and configurations, find answers to common questions about their cloud environment, and troubleshoot access and user ID issues.
- Developer Name: `<your company name>`
- Website: https://www.yourdomain.com/en.html 
- Privacy statement: https://www.yourdomain.com/en/privacy-statement.html
- Terms of use: https://www.yourdomain.com/en/terms-of-use.html
- Branding: upload appropriate images
- Under Capabilities, click Bots
- Click Set Up
- Select Existing bot
- For Bot ID, **enter MS App ID from Step 2**
- Under **Scope**, select **Personal, Team, and Group Chat**
- Click **Save**
- Note: under Domains and permissions, we not need to specify Resource Specific Consent
- Under **Finish**, **select Test and Distribute**
- Select **Download**.  This will create a deployment package (name).zip.
- On the Microsoft Teams left hand navigation bar, **select Apps**
- Select **Upload a custom app**
- Select **Upload for** `<your Teams organization>`
- Choose the `.zip` deployment package you've just downloaded.  This will add the app to Teams.
- Click the card for your new app.
- Click Add.
- Test your bot in Microsoft Teams.  

**All done!**