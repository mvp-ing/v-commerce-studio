const cardValidator = require('simple-card-validator');
const { v4: uuidv4 } = require('uuid');
const pino = require('pino');

const logger = pino({
  name: 'paymentservice-charge',
  messageKey: 'message',
  formatters: {
    level(logLevelString, logLevelNum) {
      return { severity: logLevelString };
    },
  },
});

// Get tracer for span creation
let tracer;
try {
  tracer = require('dd-trace');
} catch (e) {
  tracer = null;
}

class CreditCardError extends Error {
  constructor(message) {
    super(message);
    this.code = 400; // Invalid argument error
  }
}

class InvalidCreditCard extends CreditCardError {
  constructor(cardType) {
    super(`Credit card info is invalid`);
  }
}

class UnacceptedCreditCard extends CreditCardError {
  constructor(cardType) {
    super(
      `Sorry, we cannot process ${cardType} credit cards. Only VISA or MasterCard is accepted.`
    );
  }
}

class ExpiredCreditCard extends CreditCardError {
  constructor(number, month, year) {
    super(
      `Your credit card (ending ${number.substr(
        -4
      )}) expired on ${month}/${year}`
    );
  }
}

/**
 * Verifies the credit card number and (pretend) charges the card.
 *
 * @param {*} request
 * @return transaction_id - a random uuid.
 */
module.exports = function charge(request) {
  const { amount, credit_card: creditCard } = request;
  const cardNumber = creditCard.credit_card_number;

  // Create a span for card validation
  let validationSpan;
  if (tracer) {
    validationSpan = tracer.startSpan('card.validation', {
      childOf: tracer.scope().active(),
      tags: {
        'resource.name': 'CardValidation',
      },
    });
  }

  const cardInfo = cardValidator(cardNumber);
  const { card_type: cardType, valid } = cardInfo.getCardDetails();

  if (validationSpan) {
    validationSpan.setTag('card.type', cardType || 'unknown');
    validationSpan.setTag('card.valid', valid);
  }

  if (!valid) {
    if (validationSpan) {
      validationSpan.setTag('error', true);
      validationSpan.setTag('error.type', 'InvalidCreditCard');
      validationSpan.finish();
    }
    throw new InvalidCreditCard();
  }

  // Only VISA and mastercard is accepted, other card types (AMEX, dinersclub) will
  // throw UnacceptedCreditCard error.
  if (!(cardType === 'visa' || cardType === 'mastercard')) {
    if (validationSpan) {
      validationSpan.setTag('error', true);
      validationSpan.setTag('error.type', 'UnacceptedCreditCard');
      validationSpan.finish();
    }
    throw new UnacceptedCreditCard(cardType);
  }

  // Also validate expiration is > today.
  const currentMonth = new Date().getMonth() + 1;
  const currentYear = new Date().getFullYear();
  const {
    credit_card_expiration_year: year,
    credit_card_expiration_month: month,
  } = creditCard;

  if (currentYear * 12 + currentMonth > year * 12 + month) {
    if (validationSpan) {
      validationSpan.setTag('error', true);
      validationSpan.setTag('error.type', 'ExpiredCreditCard');
      validationSpan.finish();
    }
    throw new ExpiredCreditCard(cardNumber.replace('-', ''), month, year);
  }

  if (validationSpan) {
    validationSpan.setTag('validation.success', true);
    validationSpan.finish();
  }

  const transactionId = uuidv4();

  logger.info(`Transaction processed: ${cardType} ending ${cardNumber.substr(
    -4
  )} \
    Amount: ${amount.currency_code}${amount.units}.${amount.nanos}`);

  return { transaction_id: transactionId };
};
