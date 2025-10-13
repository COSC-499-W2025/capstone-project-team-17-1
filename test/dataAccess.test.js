const readline = require('readline');
const { getUserConsent } = require('./getUserConsent');

jest.mock('readline');

describe('getUserConsent', () => {
  let questionMock;
  let closeMock;

  // reset before each test
  beforeEach(() => {
    questionMock = jest.fn();
    closeMock = jest.fn();
    readline.createInterface.mockReturnValue({
      question: questionMock,
      close: closeMock,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  // tests positive user input
  test('returns "accepted" when user inputs "y"', async () => {
    questionMock.mockImplementationOnce((query, cb) => cb('y'));
    const result = await getUserConsent();
    expect(result).toBe('accepted');
    expect(closeMock).toHaveBeenCalled();
  });

  // tests negative user input
  test('returns "rejected" when user inputs "n"', async () => {
    questionMock.mockImplementationOnce((query, cb) => cb('n'));
    const result = await getUserConsent();
    expect(result).toBe('rejected');
    expect(closeMock).toHaveBeenCalled();
  });

  // tests invalid inputs
  test('reprompts until valid input is given', async () => {
    questionMock
      .mockImplementationOnce((query, cb) => cb('maybe'))
      .mockImplementationOnce((query, cb) => cb('y'));

    const result = await getUserConsent();
    expect(result).toBe('accepted');
    expect(questionMock).toHaveBeenCalledTimes(2);
  });
});