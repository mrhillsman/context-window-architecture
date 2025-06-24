# Google OIDC Authentication Setup Guide

This guide will help you set up Google OIDC (OpenID Connect) authentication for your Streamlit chat application.

## Prerequisites

- A Google account
- Access to Google Cloud Console
- Python environment with the required dependencies

## Step 1: Google Cloud Console Setup

### 1.1 Create a New Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "Streamlit Chat OAuth")
5. Click "Create"

### 1.2 Enable Google+ API
1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google+ API" or "Google Identity"
3. Click on "Google Identity" and then "Enable"

### 1.3 Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen:
   - User Type: External
   - App name: Your app name
   - User support email: Your email
   - Developer contact information: Your email
   - Save and continue through the remaining steps

### 1.4 Configure OAuth Client
1. Application type: Web application
2. Name: "Streamlit Chat OAuth Client"
3. Authorized redirect URIs:
   - `http://localhost:8501` (for local development)
   - `https://your-domain.com` (for production)
4. Click "Create"

### 1.5 Copy Credentials
After creating the OAuth client, you'll see:
- Client ID
- Client Secret

**Important**: Keep these credentials secure and never commit them to version control.

## Step 2: Environment Configuration

### Option A: Environment Variables (Recommended)
Set the following environment variables:

```bash
export GOOGLE_CLIENT_ID="your-client-id-here"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

### Option B: Configuration File
Update the `.config.yml` file:

```yaml
oauth_config:
  enabled: true
  provider: "google"
  client_id: "your-client-id-here"
  client_secret: "your-client-secret-here"
  redirect_uri: "http://localhost:8501"
  scope: "openid email profile"
  auth_endpoint: "https://accounts.google.com/o/oauth2/v2/auth"
  token_endpoint: "https://oauth2.googleapis.com/token"
  userinfo_endpoint: "https://www.googleapis.com/oauth2/v3/userinfo"
```

## Step 3: Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The authentication dependencies include:
- `streamlit-authenticator~=0.3.1`
- `authlib~=1.3.0`
- `itsdangerous~=2.2.0`

## Step 4: Run the Application

Start your Streamlit application:

```bash
streamlit run main.py
```

Or run a specific chatbot:

```bash
streamlit run chatbots/basic_ui_chat_with_memory.py
```

## Step 5: Test Authentication

1. Open your application in a browser
2. You should see a login page with a "Sign in with Google" button
3. Click the button to authenticate with Google
4. After successful authentication, you'll be redirected back to your application
5. Your user profile should appear in the sidebar

## Features

### Authentication Flow
- **OAuth 2.0 Authorization Code Flow**: Secure authentication using Google's OAuth 2.0
- **OpenID Connect**: Additional identity layer for user information
- **State Parameter**: CSRF protection for security
- **Token Management**: Automatic token refresh and management

### User Information
The application retrieves the following user information from Google:
- User ID (sub)
- Email address
- Full name
- Given name
- Family name
- Profile picture
- Email verification status

### Security Features
- **State Parameter**: Prevents CSRF attacks
- **Secure Token Storage**: Tokens stored in session state
- **Automatic Logout**: Session cleanup on logout
- **Error Handling**: Comprehensive error handling for authentication failures

## Configuration Options

### Enable/Disable Authentication
To disable authentication, set `enabled: false` in the oauth_config:

```yaml
oauth_config:
  enabled: false
```

### Custom Scopes
You can modify the requested scopes by updating the scope field:

```yaml
oauth_config:
  scope: "openid email profile https://www.googleapis.com/auth/calendar.readonly"
```

### Custom Redirect URI
For production deployments, update the redirect URI:

```yaml
oauth_config:
  redirect_uri: "https://your-domain.com"
```

## Troubleshooting

### Common Issues

1. **"OAuth is not properly configured"**
   - Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set
   - Check that the credentials are correct

2. **"Invalid redirect URI"**
   - Verify the redirect URI in Google Cloud Console matches your application URL
   - For local development, use `http://localhost:8501`

3. **"Authentication failed"**
   - Check the browser console for error messages
   - Verify the OAuth consent screen is configured correctly
   - Ensure the Google+ API is enabled

4. **Import errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Check that you're using the correct Python environment

### Debug Mode
To enable debug logging, add this to your application:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

### Security Considerations
1. **HTTPS**: Always use HTTPS in production
2. **Environment Variables**: Use environment variables for credentials
3. **Domain Verification**: Verify your domain in Google Cloud Console
4. **OAuth Consent Screen**: Configure the consent screen for production

### Environment Variables
Set these in your production environment:

```bash
GOOGLE_CLIENT_ID=your-production-client-id
GOOGLE_CLIENT_SECRET=your-production-client-secret
```

### Redirect URI
Update the redirect URI in both Google Cloud Console and your config:

```yaml
oauth_config:
  redirect_uri: "https://your-production-domain.com"
```

## Integration with Existing Chatbots

The authentication system is designed to work with all existing chatbots. Simply add the authentication wrapper to any chatbot:

```python
from utils.auth_wrapper import require_auth, render_auth_sidebar

@require_auth
def main():
    # Your existing chatbot code here
    render_auth_sidebar()  # Add this to show user info in sidebar
```

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your Google Cloud Console configuration
3. Check the application logs for error messages
4. Ensure all dependencies are properly installed 