/*
 * 点赞 / 喜欢 交互组件（构建块 · ArkTS NEXT 真代码，可直接接线）
 * 概念来源：GiveThumbsUp（ArkTS NEXT 真代码，点赞态切换 + 图片反馈动画）
 * 范式：点赞态切换驱动反馈动画（rotate 360° + scale + opacity，animation 平滑过渡）
 * 适老化：按钮触控区 >=48dp、stateEffect 触控反馈、点赞态读屏文案随状态变化
 * 注：GiveLike（Java API8 空 AceAbility 壳，无实质交互）的点赞范式已由本块覆盖，不单列重复块
 */

/**
 * 点赞/喜欢切换按钮 + 反馈动画包装
 * - 点击切换 liked 态，背景色与文案随之变化（高对比蓝→红，长辈可见）
 * - content 为反馈动画作用对象（如书影/题词卡），点赞时旋转放大淡出再回位
 * 用法：
 *   LikeToggle({ liked: this.$liked, label: '喜欢', content: () => { Image(...) }, onChange: (v) => {...} })
 */
@Component
export struct LikeToggle {
  @Link liked: boolean
  @Prop label: string = '点赞'
  @BuilderParam content?: () => void // 反馈动画作用对象，可留空仅显示按钮
  private onChange?: (v: boolean) => void

  build() {
    Column() {
      if (this.content) {
        this.content()
          .rotate({ x: 0, y: 1, z: 0, angle: this.liked ? 360 : 0 })
          .scale(this.liked ? { x: 1.4, y: 1.4 } : { x: 1, y: 1 })
          .opacity(this.liked ? 0.6 : 1)
          .animation({
            delay: 10,
            duration: 1000,
            iterations: 1,
            curve: Curve.Smooth,
            playMode: PlayMode.Normal
          })
      }

      Button(this.liked ? '已' + this.label : this.label, {
        type: ButtonType.Normal,
        stateEffect: true
      })
        .borderRadius(8)
        .backgroundColor(this.liked ? 0xff5533 : 0x317aff)
        .width(120)
        .height(48)
        .accessibilityText(this.liked ? '已' + this.label + '，点击取消' : '未' + this.label + '，点击' + this.label)
        .onClick(() => {
          this.liked = !this.liked
          this.onChange?.(this.liked)
        })
    }
  }
}
