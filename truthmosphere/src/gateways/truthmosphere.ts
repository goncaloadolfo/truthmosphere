import {
  FactPredictionResult,
  HeaderVerificationResult,
  NewParseResult,
  TruthResult,
} from './values'

// dummmy functions for now
// these will be replaced with actual implementations

const parseNewHTML = async (newHTML: string): Promise<NewParseResult> => {
  return {
    header: {
      id: 'header',
      content:
        'Guerra na Ucrânia. EUA ameaçam abandonar esforços para acordo de paz em poucos dias',
    },
    contentElements: [
      {
        id: 'content of the new',
        content: newHTML,
      },
    ],
  }
}

const classifyHeader = async (
  header: string
): Promise<HeaderVerificationResult> => {
  return {
    verificationResult: false,
  }
}

const classifyContent = async (
  content: string
): Promise<FactPredictionResult> => {
  return {
    predictionResult: [
      {
        fact: 'fact',
        newStatement: 'new statement',
        verificationResult: false,
      },
    ],
  }
}

const classifyNew = async (newHTML: string): Promise<TruthResult> => {
  const parseResult = await parseNewHTML(newHTML)

  const newContent = parseResult.contentElements
    .map((element) => element.content)
    .join(' ')

  const [headerResult, contentResult] = await Promise.all([
    classifyHeader(parseResult.header.content),
    classifyContent(newContent),
  ])

  return {
    parseResult,
    headerResult,
    contentResult,
  }
}

const TruthmosphereAPI = {
  classifyNew,
  parseNewHTML,
  classifyHeader,
  classifyContent,
}

export default TruthmosphereAPI
