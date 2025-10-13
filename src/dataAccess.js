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
                    user_input.close();
                    resolve(ans === 'y' ? 'accepted' : 'rejected');
                }
            });
        }
        promptConsent();
    });
}
