import { useEffect, useState } from 'react'
import { Text } from 'rebass'
import browser from 'webextension-polyfill'
import TruthmosphereAPI from '../gateways/truthmosphere'
import { TruthResult } from '../gateways/values'
import { TruthResultMessage } from '../messages'

const Popup = () => {
  const [truthfull, setTruthfull] = useState<boolean | undefined>(undefined)
  const [error, setError] = useState<string | undefined>(undefined)

  const handleTruthPredict = async () => {
    const currentTab = await browser.tabs.query({
      active: true,
      currentWindow: true,
    })

    if (currentTab.length > 0 && currentTab[0].id !== undefined) {
      const tabId = currentTab[0].id

      // get currentTab page DOM content
      const pageContent = await browser.scripting.executeScript({
        target: { tabId: tabId! },
        func: () => {
          return document.body.innerHTML
        },
      })

      // classify the new
      const newClassification = await TruthmosphereAPI.classifyNew(
        pageContent[0].result as string
      )
      const messageResult: TruthResultMessage = {
        headerResult: {
          title: newClassification.parseResult.header.content,
          verificationResult: newClassification.headerResult.verificationResult,
        },
      }
      browser.tabs.sendMessage(tabId, messageResult)

      return newClassification
    }
  }

  useEffect(() => {
    handleTruthPredict()
      .then((result: TruthResult | undefined) => {
        if (result) {
          const headerResult = result.headerResult.verificationResult
          const contentResult = result.contentResult.predictionResult

          if (!headerResult) {
            setTruthfull(false)
            setError('')
            return
          }

          if (contentResult.length > 0) {
            setTruthfull(
              contentResult.every((content) => content.verificationResult)
            )
            return
          }

          setTruthfull(true)
          setError('')
        }
      })
      .catch((error) => {
        setTruthfull(undefined)
        setError(error)
      })
  }, [])

  if (error) {
    return (
      <div className="flex flex-col gap-4 w-3xs p-4 rounded-sm">
        <Text fontSize={3} fontWeight="bold">
          Something went wrong!
        </Text>
      </div>
    )
  }

  if (truthfull === undefined) {
    return (
      <div className="flex flex-col gap-4 w-3xs p-4 rounded-sm">
        <Text fontSize={3} fontWeight="bold">
          Loading...
        </Text>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 w-3xs p-4 rounded-sm">
      {truthfull ? (
        <Text fontSize={4} fontWeight="bold">
          Truthfull New!
        </Text>
      ) : (
        <>
          <Text fontSize={4} fontWeight="bold">
            Truthless New!
          </Text>
          <div>
            <Text fontSize={1}>
              To be considered truthful, a news article must meet two key
              criteria:
            </Text>
            <div>
              <Text fontSize={1} ml={3}>
                1. <span className="font-bold">Fact Accuracy</span>: The article
                should be free from false or misleading information.
              </Text>
              <Text fontSize={1} ml={3}>
                2. <span className="font-bold">Title Integrity</span>: The title
                must clearly reflect the content and avoid bias or exaggeration.
              </Text>
            </div>
            <Text fontSize={1}>
              This ensures that both the facts and the headline are reliable and
              fair.
            </Text>
          </div>
        </>
      )}
    </div>
  )
}

export default Popup
