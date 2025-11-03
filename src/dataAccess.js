const readline = require('readline')

// get user consent from terminal
function getConsent() {
    return new Promise((resolve) => {
        const user_input = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        // asks for consent (recursive till valid input)
        function promptConsent() {
            // prompt question
            user_input.question('Do you consent to continuing with the program? (y/n): ', (answer) => {
                // generalize input
                const ans = answer.trim().toLowerCase();
                if (ans === 'y' || ans === 'n') {
                    // clode input interface
                    user_input.close();
                    // resolve based on input
                    resolve(ans === 'y' ? 'accepted' : 'rejected');
                } else {
                    // error messge for invalid input
                    console.log('Invalid input :( Please enter "y" for yes or "n" for no. Thanks :)');
                    // reprompt
                    promptConsent();
                }
            });
        }
        promptConsent();
    });
}

// save consent input to db
function saveConsent(db, consentStatus, callback) {
    // check for valid input
    if(!['accepted', 'rejected'].includes(consentStatus)) {
        return process.nextTick(() => callback(new Error('Invalid consent status :( Please use "accepted" or "rejected".')));
    }

    try {
        // get timestamp
        const timestamp = new Date().toISOString();
        const result = db
            .prepare('INSERT INTO user_consent (consent, timestamp) VALUES (?, ?)')
            .run(consentStatus, timestamp);
        process.nextTick(() => callback(null, result.lastInsertRowid));
    } catch (err) {
        process.nextTick(() => callback(err));
    }
}
module.exports = { getConsent, saveConsent };
