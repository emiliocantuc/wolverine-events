# Triggers App script that sends email to MCommunity group

# Include the app script as backup:
"""
// Function to send an email
function sendEmail(recipient, subject, body) {
  GmailApp.sendEmail(recipient, subject, body);
}

// HTTP trigger to send email
function doGet(e) {
  var secretToken = // Generate one

  // Check if the token matches
  if (e.parameter.token !== secretToken) {
    return ContentService.createTextOutput("Unauthorized request.");
  }

  // Extract email parameters
  var recipient = e.parameter.recipient;
  var subject = e.parameter.subject;
  var body = e.parameter.body;

  // Ensure all necessary parameters are provided
  if (!recipient || !subject || !body) {
    return ContentService.createTextOutput("Missing email parameters.");
  }

  try {
    sendEmail(recipient, subject, body); // Call the function to send the email
    return ContentService.createTextOutput("Email sent successfully.");
  } catch (error) {
    // Log the error for debugging
    console.error("Error sending email:", error);
    return ContentService.createTextOutput("Could not send the email.");
  }
}
"""

import requests, os, json, logging
import utils

if __name__ == '__main__':
    
    logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')    

    # Should contain 4 fields: 
    # 'token', 'url' (of the deployed app script), 'recipient', and 'subject' 
    params_file = 'email_params.json'
    body_file = 'email.txt' # Contains email body
    ntfy_channel = os.environ.get('NTFY_CHANNEL')
    if not ntfy_channel: print('Warning: no ntfy channel')

    try:

        logging.info('Trying to send email ...')

        with open(params_file, 'r') as f: params = json.loads(f.read())
        with open(body_file, 'r') as f: body = f.read()
        
        url = params['url']
        del params['url']
        params['body'] = body
        logging.info(params)

        response = requests.get(url, params = params)
        logging.info(f'response: {response.text}')
        
        if not response.text or 'not' in response.text:
            logging.error(f'Error trying to send email: {response} {response.text}')
            if ntfy_channel: utils.notify(ntfy_channel, f'Could not send email reminder')
    
    except Exception as e:
        
        logging.error(f'Error trying to send email: {e}')
        if ntfy_channel: utils.notify(ntfy_channel, f'Could not send email reminder')