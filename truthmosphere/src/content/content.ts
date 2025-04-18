import browser from 'webextension-polyfill'

browser.runtime.onMessage.addListener((message: any) => {
  console.log('Received message in content script:', message)
})
