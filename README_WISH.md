# Wish Merchant Store Setup Automation

This script automates the creation of Wish merchant stores using Playwright with concurrent workers.

## Features

- 🚀 **Automated Store Creation**: Automatically creates Wish merchant stores with random names
- 🔄 **Multi-threading Support**: Process multiple accounts concurrently
- 🤖 **Captcha Solving**: Integrated YesCaptcha API for automatic captcha solving
- 📊 **Progress Tracking**: Real-time progress bar showing completion status
- 💾 **Result Logging**: Saves successful and failed attempts to separate files

## Prerequisites

1. Python 3.8 or higher
2. Required Python packages (install via `pip install -r requirements.txt`):
   - playwright
   - undetected-playwright
   - loguru
   - tqdm
   - requests

3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## File Setup

### 1. `accounts.txt`
Contains email:password pairs (one per line):
```
email1@example.com:password1
email2@example.com:password2
email3@example.com:password3
```

### 2. `password.txt`
Contains a single password that will be used for all Wish merchant stores:
```
YourStorePassword123!
```

## YesCaptcha API Configuration

The script uses YesCaptcha API for solving captchas. The API key is configured in the script:
```python
YESCAPTCHA_CLIENT_KEY = "8d381f04402598ed227557a6acb91a6da1a909c375946"
```

Make sure you have sufficient balance in your YesCaptcha account.

## How It Works

1. **Opens Wish Merchant Signup**: Navigates to `https://merchant.wish.com/open-express?r=802OI`

2. **Fills Store Name**: Generates a random 12-character store name (letters + numbers)

3. **Enters Email**: Uses email from `accounts.txt`

4. **Enters Password**: Uses password from `password.txt`

5. **Solves Captcha**:
   - Captures the captcha image from the page
   - Converts it to base64
   - Sends to YesCaptcha API for OCR
   - Enters the solved captcha text

6. **Submits Form**: Clicks the Continue button

7. **Logs Results**: Saves successful creations to `completed.txt` and failures to `failed.txt`

## Usage

1. Make sure all required files are set up:
   - `accounts.txt` with your email accounts
   - `password.txt` with your store password

2. Run the script:
   ```bash
   python wish_store_automation.py
   ```

3. When prompted, enter the number of concurrent workers:
   ```
   Number of concurrent workers: 5
   ```

4. The script will:
   - Process all accounts from `accounts.txt`
   - Run multiple workers in parallel
   - Show progress bar with completion status
   - Save results to `completed.txt` and `failed.txt`

## Output Files

- **`completed.txt`**: Successfully created stores
  ```
  email@example.com:password - Store: RandomName12
  ```

- **`failed.txt`**: Failed attempts with error messages
  ```
  email@example.com - Error: Captcha solving failed
  ```

## Features in Detail

### Random Store Name Generation
- Generates 12 random characters (letters + numbers)
- Unique for each store creation attempt
- Example: `aB3xT9kL2pQ1`

### Human-like Behavior
- Random typing delays between characters
- Mouse movement simulation before clicks
- Random delays between actions
- Helps avoid detection

### Captcha Solving Process
1. Detects captcha image on page
2. Downloads captcha image bytes
3. Converts to base64 format
4. Sends to YesCaptcha API with task type `ImageToTextTaskMuggle`
5. Polls API every 2 seconds for result (max 60 seconds)
6. Returns solved text and fills into form

### Thread-Safe Operations
- File operations use locks to prevent race conditions
- Safe for concurrent workers
- Progress bar updates atomically

## Troubleshooting

### Script fails to find elements
- Check if Wish has changed their page structure
- Update CSS selectors in the script if needed

### Captcha solving fails
- Check YesCaptcha API balance
- Verify API key is correct
- Check network connectivity

### Browser doesn't open
- Make sure Playwright browsers are installed: `playwright install chromium`
- Check system requirements for running Chrome

### Workers are too slow
- Reduce number of concurrent workers
- Check system resources (CPU, RAM)

## Performance Tips

- **Worker Count**: Start with 2-3 workers and increase based on system performance
- **Network**: Ensure stable internet connection for captcha API calls
- **System Resources**: Each worker opens a browser instance (requires ~200-300MB RAM)

## Security Notes

- Store API keys securely
- Don't share your `accounts.txt` or `password.txt` files
- Use unique passwords for each service
- Be aware of Wish's terms of service regarding automation

## Example Run

```
Wish Merchant Store Setup Automation Script
==================================================
Loaded 10 accounts from accounts.txt
Loaded store password from password.txt
Created 10 tasks
Number of concurrent workers: 3

Progress: 100%|████████████████████████| 10/10 [05:32<00:00, 33.2s/account]

Script finished!
Press Enter to exit...
```

## Support

For issues or questions:
1. Check the log output for detailed error messages
2. Verify all input files are properly formatted
3. Ensure YesCaptcha API is working and has balance

## License

This script is for educational and authorized use only. Make sure you comply with Wish's terms of service.
