const assert = require('assert');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { saveConsent, getConsent } = require('../src/dataAccess.js');
const { connect, initSchema } = require('../src/db/consentDB.js');

// create temp db file for testing
const testDbPath = path.resolve('./temp_test_consentDB.sqlite');

const test = require('node:test');

/*
 * Monkey patch readline so getConsent sees a scripted sequence of answers.
 * Returns a restore fn that rewinds createInterface and exposes call counts.
 */

describe('Consent Recording', () => {
  let db; // hold sqlite connection
  before(() => {
    process.env.CONSENT_DB_PATH = testDbPath; // set environment vari
    db = connect(); // open connection
    initSchema(db);
  });

  // housekeeping -> close db and delete temp file
  after(() => {
    db.close();
    if (fs.existsSync(testDbPath)) 
      fs.unlinkSync(testDbPath);
    delete process.env.CONSENT_DB_PATH;
  });

  // test for saving consent
  it('store user consent in db', (done) => {
    saveConsent(db, 'accepted', (err, cid) => {
      assert.ifError(err);
      db.get('SELECT status FROM user_consent WHERE consent_id=?', [cid], (err, row) => {
        assert.ifError(err);
        assert.strictEqual(row.consent, 'accepted');
        done();
      });
    });
  });
});

// fake terminal input for tests
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
