const readline = require('readline')

function getConsent() {
    return new Promise((resolve) => {
        const user_input = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });

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

module.exports = { getConsent };
