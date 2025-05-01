import { useEffect, useState } from 'react'
import { ThreeDots } from 'react-loading-icons'
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
      console.log('tabId', tabId)

      // get currentTab page DOM content
      let contentRes: DocumentResponse | undefined
      try {
        const contentRequest: RequestContent = { type: RequestType.GET_CONTENT }
        const contentRes = await browser.tabs.sendMessage(tabId, contentRequest)
        console.log('contentRes', contentRes)
      } catch (error) {
        throw new Error(
          'Unable to get content from current tab, make sure the page is within the domain whitelist.'
        )
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
      console.log('messageResult', messageResult)

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
        console.error('Error:', error)
        setTruthfull(undefined)
        setError(error.message)
      })
  }, [])

  if (error) {
    return (
      <div className="flex flex-col gap-2 w-xs p-1 text-rederrors text-center">
        <Text fontSize={2} fontWeight={'bold'}>
          <span className="text-2xl">⚠️</span> Unable to load content from this
          tab.
        </Text>
        <Text fontSize={1}>{error}</Text>
      </div>
    )
  }

  if (truthfull === undefined) {
    return (
      <div className="flex flex-col justify-center items-center w-xs p-4">
        <ThreeDots stroke="#52C41A" speed={0.75} width={'84px'} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 w-xs">
      <div
        className={`w-full text-center ${truthfull ? 'bg-truthgreen' : 'bg-truthred'}`}
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
