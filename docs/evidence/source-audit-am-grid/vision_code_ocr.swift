import Foundation
import Vision
import AppKit

// Independent, local pixel transcription. No language correction, dictionary,
// candidate code, or source text is supplied to the recognizer.
let path = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: path),
      let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fatalError("Cannot load the diagnostic source crop")
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["en-US"]
try VNImageRequestHandler(cgImage: cg).perform([request])
let results = (request.results ?? []).map { observation -> [String: Any] in
    let candidates = observation.topCandidates(3).map {
        ["text": $0.string, "confidence": $0.confidence] as [String: Any]
    }
    return ["candidates": candidates,
            "bbox": [observation.boundingBox.minX, observation.boundingBox.minY,
                     observation.boundingBox.width, observation.boundingBox.height]]
}
let framework = Bundle(for: VNRecognizeTextRequest.self)
let output: [String: Any] = [
    "engine": "Apple Vision VNRecognizeTextRequest",
    "revision": request.revision,
    "framework_version": framework.object(forInfoDictionaryKey: "CFBundleVersion") ?? "unknown",
    "operating_system": ProcessInfo.processInfo.operatingSystemVersionString,
    "languageCorrection": false,
    "language": "en-US",
    "results": results
]
let data = try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
