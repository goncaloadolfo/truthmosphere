interface HeaderVerificationResult {
  title: string
  verificationResult: boolean
}

interface TruthResultMessage {
  headerResult: HeaderVerificationResult
}

export type { HeaderVerificationResult, TruthResultMessage }
