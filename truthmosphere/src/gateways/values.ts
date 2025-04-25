interface NewElement {
  selector: string
  content: string
}

interface NewParseResult {
  header: NewElement
  contentElements: NewElement[]
}

interface HeaderVerificationResult {
  verificationResult: boolean
}

interface FactPredictionResult {
  verificationResult: boolean
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
