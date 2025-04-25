enum RequestType {
  GET_CONTENT = 'GET_CONTENT',
}

interface RequestContent {
  type: RequestType
}

interface DocumentResponse {
  content: string
}

interface HeaderVerificationResult {
  selector: string
  title: string
  verificationResult: boolean
}

interface TruthResultMessage {
  headerResult: HeaderVerificationResult
}

export { RequestType }

export type {
  DocumentResponse,
  HeaderVerificationResult,
  RequestContent,
  TruthResultMessage,
}
