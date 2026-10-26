import SwiftUI
import AVFoundation
#if os(macOS)
import AppKit
#endif

/// 短音播放（镜像 HarmonyOS 版 SoundPlayer.ets / @kit.AudioKit SoundPool）：
/// iOS 用 AVAudioPlayer，macOS 用 NSSound；无资源时静默降级（生存）。
public struct SoundPlayer: View {
    @State private var playing = false

    public init() {}

    public var body: some View {
        VStack(spacing: 10) {
            Button(playing ? "停止" : "播放提示音") {
                playShort()
                playing.toggle()
            }
            .padding()
            Text("短音播放（镜像 @kit.AudioKit SoundPool；包内放 tip.wav 即生效）")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func playShort() {
        #if os(iOS)
        if let url = Bundle.main.url(forResource: "tip", withExtension: "wav") {
            try? AVAudioPlayer(contentsOf: url)?.play()
        }
        #elseif os(macOS)
        if let url = Bundle.main.url(forResource: "tip", withExtension: "wav") {
            NSSound(contentsOf: url, byReference: false)?.play()
        }
        #endif
    }
}
