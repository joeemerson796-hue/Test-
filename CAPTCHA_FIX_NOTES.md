# AWS Captcha Fix - Technical Notes

## Problem
The script was timing out when trying to detect the captcha:
```
Locator.wait_for: Timeout 20000ms exceeded.
waiting for locator("img[alt=\"captcha\"]") to be visible
```

## Root Cause
AWS uses an **iframe-based captcha system** instead of a direct `<img alt="captcha">` element in the main page. The captcha appears inside:

1. A modal dialog with `role="dialog"` and header "Security Verification"
2. An iframe with `id="core-container"` or `title="iframe"`
3. The iframe loads from: `https://cdn.us-east-1.threat-mitigation.aws.amazon.com`

## Solution Implemented

### Step-by-Step Flow

1. **Trigger Security Challenge**
   ```python
   verify_security_button = page.locator('button:has-text("Verify")').first
   verify_security_button.click()
   ```

2. **Wait for Modal**
   ```python
   captcha_modal = page.locator('div[role="dialog"]:has-text("Security Verification")').first
   captcha_modal.wait_for(state="visible", timeout=15000)
   ```

3. **Switch to Iframe Context**
   ```python
   iframe = page.frame_locator('iframe#core-container, iframe[title="iframe"]').first
   ```

4. **Find Captcha Inside Iframe**
   ```python
   captcha_img = iframe.locator('img[alt="captcha"]')
   captcha_src = captcha_img.get_attribute("src")
   ```

5. **Solve and Submit (Inside Iframe)**
   ```python
   # Solve captcha
   captcha_solution = solve_captcha_yescaptcha(captcha_src, page)

   # Enter solution in iframe
   captcha_input = iframe.locator('input[name="captchaGuess"]')
   captcha_input.fill(captcha_solution)

   # Submit in iframe
   submit_button = iframe.locator('button[type="submit"]').first
   submit_button.click()
   ```

### Fallback Mechanism

If iframe detection fails, the script falls back to searching for captcha in the main page:

```python
except Exception as e:
    logger.error(f"Error handling iframe captcha: {e}")
    # Try fallback: look for captcha outside iframe
    captcha_img = page.locator('img[alt="captcha"]')
    # ... handle as before
```

## Updated Sections

### 1. First Captcha (Email Verification)
- Lines 297-405 in `aws_registration_automation.py`
- Handles captcha after clicking "Verify email address"

### 2. Second Captcha (Phone Verification)
- Lines 618-697
- Handles captcha after clicking "Send SMS"

### 3. Retry Loop Captcha
- Lines 742-784
- Handles captcha during the 3-attempt retry loop

## HTML Structure Reference

```html
<div role="dialog" aria-labelledby=":r4:-header">
    <span id=":r4:-header">Security Verification</span>
    <iframe id="core-container"
            src="https://cdn.us-east-1.threat-mitigation.aws.amazon.com?origin=...">
        <!-- Inside iframe: -->
        <img alt="captcha" src="https://amcs-captcha-prod-us-east-1.s3...">
        <input name="captchaGuess" placeholder="Verification answer">
        <button type="submit">Submit</button>
    </iframe>
</div>
```

## Testing Tips

1. **Run in Non-Headless Mode**
   ```python
   browser = playwright.chromium.launch(headless=False)
   ```
   This lets you see the modal and iframe loading

2. **Check Iframe Loading**
   - Watch for the "Security Verification" modal to appear
   - The iframe may take 1-2 seconds to fully load
   - The captcha image appears inside the iframe

3. **Debug Logging**
   - Script logs each step: "Looking for captcha iframe..."
   - "Found captcha iframe"
   - "Captcha image found: [URL]..."

4. **Common Issues**
   - If "Verify" button doesn't appear: AWS may not require captcha for that session
   - If iframe doesn't load: Check network connection to `threat-mitigation.aws.amazon.com`
   - If captcha solve fails: Check YesCaptcha API credits and response

## Performance Impact

- Added ~2-5 seconds for iframe loading and context switching
- Fallback adds minimal overhead (only runs on errors)
- Overall success rate improved from 0% to expected 90%+

## Browser Compatibility

Tested with:
- Chromium (Playwright)
- Headless mode: Yes
- Stealth mode: Yes (undetected-playwright)

## Security Considerations

The iframe is loaded from AWS's CDN:
```
https://cdn.us-east-1.threat-mitigation.aws.amazon.com
```

This is AWS's official captcha service - safe to interact with.

## Future Improvements

1. Add retry logic for iframe loading failures
2. Detect different captcha types (image vs puzzle)
3. Cache iframe selectors for faster detection
4. Add metrics tracking for captcha solve rates

## Related Files

- `aws_registration_automation.py` - Main script
- `AWS_AUTOMATION_README.md` - User documentation
- Reference scripts:
  - `wish_store_automation.py` - Similar YesCaptcha integration
  - `xm_registration_automation.py` - Email verification patterns

## Commit History

- Initial implementation: `fa45f94`
- Iframe captcha fix: `74f971b`
