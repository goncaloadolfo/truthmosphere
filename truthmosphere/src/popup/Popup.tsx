import { useEffect, useState } from 'react'
import { Text } from 'rebass'
import browser from 'webextension-polyfill'
import TruthmosphereAPI from '../gateways/truthmosphere'
import { TruthResult } from '../gateways/values'
import {
  DocumentResponse,
  RequestContent,
  RequestType,
  TruthResultMessage,
} from '../messages'

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
      const contentRequest: RequestContent = { type: RequestType.GET_CONTENT }
      const contentRes = await browser.tabs.sendMessage(tabId, contentRequest)

      if (!contentRes) {
        throw new Error('Failed to get page content')
      }
      const pageContent = (contentRes as DocumentResponse)?.content

      // classify the new
      const newClassification = await TruthmosphereAPI.classifyNew(pageContent)
      const messageResult: TruthResultMessage = {
        headerResult: {
          selector: newClassification.parseResult.header.selector,
          title: newClassification.parseResult.header.content,
          verificationResult: newClassification.headerResult.verificationResult,
        },
      }
      await browser.tabs.sendMessage(tabId, messageResult)

      return newClassification
    }
  }

  useEffect(() => {
    handleTruthPredict()
      .then((result: TruthResult | undefined) => {
        if (result) {
          const headerResult = result.headerResult.verificationResult
          const contentResult = result.contentResult.verificationResult
          setTruthfull(headerResult && contentResult)
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
    <div className="flex flex-col gap-4 w-xs rounded-sm">
      <div
        className={`w-full text-center rounded-sm ${truthfull ? 'bg-truthgreen' : 'bg-truthred'}`}
      >
        <Text fontSize={4} color={'white'}>
          {truthfull ? 'Truthfull New!' : 'Truthless New!'}
        </Text>
      </div>
      <div className="bg-truthdarkgrey h-px mx-2" />
      <div
        className={`mx-2 ${truthfull ? 'text-truthgreen' : 'text-truthred'}`}
      >
        <Text fontSize={3} fontWeight="bold">
          Criteria
        </Text>
        <div className="flex flex-col gap-2 text-truthdarkgrey">
          <Text fontSize={1}>
            To be considered truthful, a news article must meet two key
            criteria:
          </Text>
          <div className="flex flex-col gap-2 ml-2">
            <Text fontSize={1}>
              <span className={truthfull ? 'text-truthgreen' : 'text-truthred'}>
                ★
              </span>{' '}
              <span className="font-bold">Fact Accuracy</span>: The article
              should be free from false or misleading information.
            </Text>
            <Text fontSize={1}>
              <span className={truthfull ? 'text-truthgreen' : 'text-truthred'}>
                ★
              </span>{' '}
              <span className="font-bold">Title Integrity</span>: The title must
              clearly reflect the content and avoid bias or exaggeration.
            </Text>
          </div>
          <Text fontSize={1}>
            This ensures that both the facts and the headline are reliable and
            fair.
          </Text>
        </div>
      </div>
    </div>
  )
}

export default Popup
