interface NewElement {
  id?: string
  content: string
}

interface NewParseResult {
  header: NewElement
  contentElements: NewElement[]
}

interface HeaderVerificationResult {
  verificationResult: boolean
}

interface FactResult {
  fact: string
  newStatement: string
  verificationResult: boolean
}

interface FactPredictionResult {
  predictionResult: FactResult[]
}

interface TruthResult {
  parseResult: NewParseResult
  headerResult: HeaderVerificationResult
  contentResult: FactPredictionResult
}

export type {
  FactPredictionResult,
  HeaderVerificationResult,
  NewParseResult,
  TruthResult,
}
