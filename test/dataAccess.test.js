const assert = require('node:assert/strict');
const test = require('node:test');
const readline = require('node:readline');
const { getConsent } = require('../src/dataAccess');

/**
 * Monkey patch readline so getConsent sees a scripted sequence of answers.
 * Returns a restore fn that rewinds createInterface and exposes call counts.
 */
function stubReadline(responses) {
  const originalCreateInterface = readline.createInterface;
  let questionCalls = 0;
  let closeCalls = 0;

  readline.createInterface = () => ({
    question(_prompt, cb) {
      const idx = Math.min(questionCalls, responses.length - 1);
      questionCalls += 1;
      cb(responses[idx]);
    },
    close() {
      closeCalls += 1;
    }
  });

  return () => {
    readline.createInterface = originalCreateInterface;
    return { questionCalls, closeCalls };
  };
}

test.describe('getConsent', () => {
  test.it('returns "accepted" when user inputs y', async (t) => {
    const restore = stubReadline(['y']);
    let stats;
    try {
      const result = await getConsent();
      assert.strictEqual(result, 'accepted');
    } finally {
      stats = restore();
    }
    assert.strictEqual(stats.questionCalls, 1);
    assert.strictEqual(stats.closeCalls, 1);
  });

  test.it('returns "rejected" when user inputs n', async () => {
    const restore = stubReadline(['n']);
    let stats;
    try {
      const result = await getConsent();
      assert.strictEqual(result, 'rejected');
    } finally {
      stats = restore();
    }
    assert.strictEqual(stats.questionCalls, 1);
    assert.strictEqual(stats.closeCalls, 1);
  });

  test.it('reprompts until a valid input is given', async () => {
    const restore = stubReadline(['maybe', 'y']);
    let stats;
    try {
      const result = await getConsent();
      assert.strictEqual(result, 'accepted');
    } finally {
      stats = restore();
    }
    assert.strictEqual(stats.questionCalls, 2);
    assert.strictEqual(stats.closeCalls, 1);
  });
});
