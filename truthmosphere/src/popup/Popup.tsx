import { Text } from 'rebass'

type PopupProps = {
  truthfull: boolean
}

const Popup = ({ truthfull }: PopupProps) => {
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
