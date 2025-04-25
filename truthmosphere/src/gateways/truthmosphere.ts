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
      selector: '.arr--story--headline-h1',
      content:
        'Agitação marítima, chuva e queda de neve. Há nove distritos sob aviso laranja',
    },
    contentElements: [
      {
        selector: '.arr--story--content',
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
    verificationResult: true,
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
