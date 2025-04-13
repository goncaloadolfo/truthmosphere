import React from 'react'
import browser from 'webextension-polyfill'

function App() {
  const updateBackgroundColor = async () => {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true })
    const currentTabId = tabs?.[0].id

    if (currentTabId) {
      await browser.scripting.executeScript({
        target: { tabId: currentTabId },
        func: () => {
          document.body.style.backgroundColor = 'lightblue'
        },
      })
    }
  }

  return (
    <div>
      <div className="text-3xl font-bold underline">Hello World!</div>
      <button
        onClick={updateBackgroundColor}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
      >
        Change Background Color
      </button>
    </div>
  )
}

export default App
