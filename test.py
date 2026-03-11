from playwright.sync_api import sync_playwright
import time
import os


def publish_xiaohongshu(title, content, image_path=None):

    with sync_playwright() as p:

        print("启动浏览器...")

        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )

        context = browser.new_context()

        page = context.new_page()

        # 打开创作中心
        page.goto("https://creator.xiaohongshu.com")

        print("请扫码登录小红书，然后按回车继续...")
        input()

        # 进入发布页面
        page.goto("https://creator.xiaohongshu.com/publish/publish")

        print("等待页面加载...")
        page.wait_for_timeout(6000)

        # =====================
        # 上传图片（如果有）
        # =====================
        if image_path and os.path.exists(image_path):

            print("上传图片:", image_path)

            try:
                page.set_input_files("input[type=file]", image_path)
                time.sleep(5)
            except Exception as e:
                print("图片上传失败:", e)

        # =====================
        # 填写标题
        # =====================

        try:

            print("填写标题...")

            title_box = page.get_by_placeholder("填写标题")

            title_box.click()
            title_box.fill(title)

        except Exception as e:
            print("标题填写失败:", e)

        # =====================
        # 填写正文
        # =====================

        try:

            print("填写正文...")

            editor = page.locator("[contenteditable='true']").first

            editor.click()
            editor.fill(content)

        except Exception as e:
            print("正文填写失败:", e)

        time.sleep(3)

        # =====================
        # 点击发布
        # =====================

        try:

            print("点击发布...")

            publish_btn = page.get_by_role("button", name="发布")

            publish_btn.click()

            print("发布操作已执行")

        except Exception as e:
            print("发布失败:", e)

        print("等待发布完成...")

        time.sleep(10)

        browser.close()


def main():

    print("========== 小红书自动发布测试 ==========\n")

    title = input("请输入标题：")

    print("\n请输入正文内容：")
    content = input()

    image_path = input("\n如果需要上传图片请输入图片路径（直接回车跳过）：")

    print("\n========== 发布内容 ==========")

    print("标题:", title)
    print("正文:", content)

    if image_path:
        print("图片:", image_path)

    confirm = input("\n确认发布？(y/n)：")

    if confirm.lower() == "y":
        publish_xiaohongshu(title, content, image_path)
    else:
        print("已取消发布")


if __name__ == "__main__":
    main()