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
export function saveConsent(db, consentStatus, callback) {
    // check for valid input
    if(!['accepted', 'rejected'].includes(consentStatus)) {
        return callback(new Error('Invalid consent status :( Please use "accepted" or "rejected".'));
    }

    // get timestamp
    const timestamp = new Date().toISOString();
    db.run(
        // insert into db
        'INSERT INTO user_consent (consent, timestamp) VALUES (?, ?)',
        [consentStatus, timestamp],
        function(err) {
            if (err) {
                return callback(err);
                callback(null, this.lastID);
            }
        }
    );

}
module.exports = { getConsent };
