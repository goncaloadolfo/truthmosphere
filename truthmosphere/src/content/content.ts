import browser from 'webextension-polyfill'
import {
  HeaderVerificationResult,
  RequestType,
  TruthResultMessage,
} from '../messages'

const setupUnverifiedTooltip = (): HTMLDivElement => {
  const tooltip = document.createElement('div')

  tooltip.id = 'truthmosphere-tooltip'
  tooltip.style.position = 'absolute'
  tooltip.style.padding = '5px'
  tooltip.style.border = '1px solid #ccc'
  tooltip.style.borderRadius = '5px'
  tooltip.style.zIndex = '9999'
  tooltip.style.width = '170px'
  tooltip.style.display = 'none'
  tooltip.style.opacity = '0'
  tooltip.style.pointerEvents = 'none'
  tooltip.style.color = 'black'
  tooltip.style.backgroundColor = 'white'
  tooltip.style.fontSize = '14px'
  tooltip.style.lineHeight = '1.5'
  tooltip.style.top = '100%'
  tooltip.style.marginTop = '5px'

  tooltip.textContent = `
  This header has been classified as misleading or sensationalist. 
  Please verify the information before trusting it.
  `

  return tooltip
}

const setupVerifiedIcon = (verified: boolean): HTMLDivElement => {
  const iconContainer = document.createElement('div')

  iconContainer.id = 'truthmosphere-verification-icon'
  iconContainer.style.width = '30px'
  iconContainer.style.height = '30px'
  iconContainer.style.borderRadius = '50%'
  iconContainer.style.position = 'absolute'
  iconContainer.style.display = 'flex'
  iconContainer.style.alignItems = 'center'
  iconContainer.style.justifyContent = 'center'
  iconContainer.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)'
  iconContainer.style.fontSize = '24px'
  iconContainer.style.color = 'white'
  iconContainer.style.fontWeight = 'bold'
  iconContainer.style.top = '10px'
  iconContainer.style.right = '-30px'
  iconContainer.style.zIndex = '9999'
  iconContainer.textContent = verified ? '✔' : '✖'

  if (verified) {
    iconContainer.style.backgroundColor = 'green'
  } else {
    iconContainer.style.backgroundColor = 'red'

    // setup tooltip for unverified
    const tooltip = setupUnverifiedTooltip()
    iconContainer.appendChild(tooltip)

    iconContainer.addEventListener('mouseover', () => {
      tooltip.style.display = 'block'
      tooltip.style.opacity = '1'
    })

    iconContainer.addEventListener('mouseout', () => {
      tooltip.style.display = 'none'
      tooltip.style.opacity = '0'
    })
  }

  return iconContainer
}

const changeHeaderStyle = (headerResult: HeaderVerificationResult) => {
  const verificationResult = headerResult.verificationResult
  const headerSelector = headerResult.selector
  const headerElem = document.querySelector(headerSelector)

  // remove existing icon if it exists
  const existingIcon = document.getElementById(
    'truthmosphere-verification-icon'
  )
  if (existingIcon) {
    existingIcon.remove()
  }

  if (headerElem) {
    const header = headerElem as HTMLElement
    const icon = setupVerifiedIcon(verificationResult)
    header.style.position = 'relative'
    header.appendChild(icon)
  }
}

const handleMessage = (message: any): Promise<any> => {
  if (message?.type && message.type === RequestType.GET_CONTENT) {
    const content = document.body.innerHTML
    return Promise.resolve({ content })
  }

  if (message?.headerResult) {
    const truthResultMessage: TruthResultMessage = message
    changeHeaderStyle(message.headerResult)
    return Promise.resolve({ status: 'success' })
  }

  return Promise.reject(new Error('Unknown message type from popup'))
}

browser.runtime.onMessage.addListener(handleMessage)
