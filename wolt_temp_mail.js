const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

// Helper function to generate random string
function randomString(length) {
    const chars = 'abcdefghijklmnopqrstuvwxyz';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result.charAt(0).toUpperCase() + result.slice(1);
}

// Helper function to sleep
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper function to clean verification link
function cleanVerificationLink(htmlContent) {
    // Extract the verification link from HTML
    const linkMatch = htmlContent.match(/href="(https:\/\/wolt\.com\/me\/magic_login[^"]+)"/);
    if (!linkMatch) return null;

    // Remove &amp; and replace with &
    return linkMatch[1].replace(/&amp;/g, '&');
}

async function createWoltAccount(apiKey, phoneNumber, workerNum) {
    const browser = await chromium.launch({
        headless: false,
        args: ['--disable-blink-features=AutomationControlled']
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();

    try {
        console.log(`[Worker ${workerNum}] Starting account creation with phone: ${phoneNumber}`);

        // Step 1: Get random email from temp mail API
        console.log(`[Worker ${workerNum}] Getting temp email...`);
        const emailResponse = await page.request.get(`https://free.priyo.email/api/random-email/${apiKey}`);
        const emailData = await emailResponse.text();
        const emailMatch = emailData.match(/"email":"([^"]+)","password":"([^"]+)"/);

        if (!emailMatch) {
            throw new Error('Failed to get email from API');
        }

        const email = emailMatch[1];
        const emailPassword = emailMatch[2];
        console.log(`[Worker ${workerNum}] Got email: ${email}`);

        // Step 2: Go to wolt.com
        console.log(`[Worker ${workerNum}] Opening wolt.com...`);
        await page.goto('https://wolt.com/', { waitUntil: 'networkidle', timeout: 60000 });
        await sleep(2000);

        // Step 3: Click Sign up button
        console.log(`[Worker ${workerNum}] Clicking Sign up...`);
        await page.click('button[data-test-id="UserStatus.Signup"]');
        await sleep(3000);

        // Step 4: Enter email in iframe
        console.log(`[Worker ${workerNum}] Entering email...`);
        const frame = page.frameLocator('iframe').first();
        await frame.locator('input[data-test-id="MethodSelect.EmailInput"]').fill(email);
        await sleep(1000);

        // Step 5: Click Continue
        console.log(`[Worker ${workerNum}] Clicking Continue...`);
        await frame.locator('button[data-test-id="StepMethodSelect.NextButton"]').click();

        // Step 6: Wait for "Great, check your inbox!"
        console.log(`[Worker ${workerNum}] Waiting for confirmation...`);
        await frame.locator('h2:has-text("Great, check your inbox!")').waitFor({ timeout: 30000 });
        console.log(`[Worker ${workerNum}] Email sent confirmation received`);
        await sleep(3000);

        // Step 7: Fetch email messages from API
        console.log(`[Worker ${workerNum}] Checking inbox for verification email...`);
        let verificationLink = null;
        let attempts = 0;

        while (!verificationLink && attempts < 20) {
            await sleep(3000);
            attempts++;
            console.log(`[Worker ${workerNum}] Attempt ${attempts}/20 to fetch email...`);

            const messagesResponse = await page.request.get(`https://free.priyo.email/api/messages/${email}/${apiKey}`);
            const messages = await messagesResponse.json();

            if (messages && messages.length > 0) {
                for (const message of messages) {
                    if (message.sender_email === 'info@wolt.com' && message.subject.includes('Welcome to Wolt')) {
                        verificationLink = cleanVerificationLink(message.content);
                        if (verificationLink) {
                            console.log(`[Worker ${workerNum}] Found verification link`);
                            break;
                        }
                    }
                }
            }
        }

        if (!verificationLink) {
            throw new Error('Failed to get verification email');
        }

        // Step 8: Open verification link
        console.log(`[Worker ${workerNum}] Opening verification link...`);
        await page.goto(verificationLink, { waitUntil: 'networkidle', timeout: 60000 });
        await sleep(3000);

        // Step 9: Select Hungary as country
        console.log(`[Worker ${workerNum}] Selecting country Hungary...`);
        const frame2 = page.frameLocator('iframe').first();
        await frame2.locator('input#CreateAccount\\.Country').click();
        await sleep(1000);
        await frame2.locator('li:has-text("Hungary")').first().click();
        await sleep(1000);

        // Step 10: Enter first name (9 random chars)
        const firstName = randomString(9);
        console.log(`[Worker ${workerNum}] Entering first name: ${firstName}`);
        await frame2.locator('input[data-test-id="CreateAccount.FirstName"]').fill(firstName);
        await sleep(500);

        // Step 11: Enter last name (10 random chars)
        const lastName = randomString(10);
        console.log(`[Worker ${workerNum}] Entering last name: ${lastName}`);
        await frame2.locator('input[data-test-id="CreateAccount.LastName"]').fill(lastName);
        await sleep(500);

        // Step 12: Select Ukraine (+380) for phone country
        console.log(`[Worker ${workerNum}] Selecting phone country Ukraine...`);
        await frame2.locator('input#CreateAccount\\.PhoneNumberCountryCode').click();
        await sleep(1000);
        await frame2.locator('li:has-text("Ukraine")').first().click();
        await sleep(1000);

        // Step 13: Enter phone number
        console.log(`[Worker ${workerNum}] Entering phone number: ${phoneNumber}`);
        await frame2.locator('input[data-test-id="CreateAccount.PhoneNumber"]').fill(phoneNumber);
        await sleep(1000);

        // Step 14: Click Next
        console.log(`[Worker ${workerNum}] Clicking Next...`);
        await frame2.locator('button[data-test-id="CreateAccount.Continue"]').click();
        await sleep(3000);

        // Step 15: Click "Send code by SMS"
        console.log(`[Worker ${workerNum}] Clicking Send code by SMS...`);
        await frame2.locator('button[data-test-id="VerifyPhoneNumberMethodSelect.SmsButton"]').click();
        await sleep(3000);

        // Step 16: Resend SMS 4 times
        for (let i = 0; i < 4; i++) {
            console.log(`[Worker ${workerNum}] Resend attempt ${i + 1}/4...`);

            // Click "I didn't get a code"
            await frame2.locator('button[data-test-id="VerifyCode.CodeNotReceived"]').click();
            await sleep(2000);

            // Click "Resend code by SMS"
            await frame2.locator('button[data-test-id="NoCodeReceived.SmsButton"]').click();
            await sleep(3000);
        }

        console.log(`[Worker ${workerNum}] ✅ Successfully completed 4 SMS resends for ${phoneNumber}`);
        console.log(`[Worker ${workerNum}] Account details: ${email} | ${firstName} ${lastName} | ${phoneNumber}`);

        // Save account info
        const accountInfo = `Email: ${email} | Password: ${emailPassword} | Name: ${firstName} ${lastName} | Phone: +380${phoneNumber}\n`;
        await fs.appendFile('wolt_accounts.txt', accountInfo);

    } catch (error) {
        console.error(`[Worker ${workerNum}] ❌ Error:`, error.message);
    } finally {
        await browser.close();
        console.log(`[Worker ${workerNum}] Browser closed`);
    }
}

async function main() {
    try {
        // Read API keys
        const keysContent = await fs.readFile('keys.txt', 'utf-8');
        const keys = keysContent.trim().split('\n').filter(k => k.trim());

        if (keys.length === 0) {
            console.error('No API keys found in keys.txt');
            return;
        }

        // Read phone numbers
        const numbersContent = await fs.readFile('numbers.txt', 'utf-8');
        const numbers = numbersContent.trim().split('\n').filter(n => n.trim());

        if (numbers.length === 0) {
            console.error('No phone numbers found in numbers.txt');
            return;
        }

        console.log(`Found ${keys.length} API keys and ${numbers.length} phone numbers`);

        // Process accounts (can adjust concurrent workers)
        const maxConcurrentWorkers = 3; // Adjust based on your system

        for (let i = 0; i < numbers.length; i += maxConcurrentWorkers) {
            const batch = [];

            for (let j = 0; j < maxConcurrentWorkers && (i + j) < numbers.length; j++) {
                const index = i + j;
                const apiKey = keys[index % keys.length]; // Rotate through keys
                const phoneNumber = numbers[index].trim();
                const workerNum = index + 1;

                batch.push(createWoltAccount(apiKey, phoneNumber, workerNum));
            }

            // Wait for current batch to complete
            await Promise.all(batch);

            console.log(`\n--- Batch completed (${i + batch.length}/${numbers.length}) ---\n`);

            // Small delay between batches
            if (i + maxConcurrentWorkers < numbers.length) {
                await sleep(2000);
            }
        }

        console.log('\n✅ All accounts processed!');

    } catch (error) {
        console.error('Fatal error:', error);
    }
}

main();
