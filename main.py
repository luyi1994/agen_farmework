import typer
import asyncio
import uvicorn

app = typer.Typer(help="通用 Agent 框架 CLI")


@app.command()
def chat(
    session_id: str = typer.Option("cli_user", help="会话 ID"),
):
    """启动交互式 CLI 对话"""
    from core.agent import Agent

    typer.echo("Agent 初始化中...")
    agent = Agent()
    typer.echo("✓ Agent 就绪，输入 'exit' 退出\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("\n再见！")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            typer.echo("再见！")
            break
        if not user_input:
            continue

        result = asyncio.run(agent.chat(user_input, session_id))
        typer.echo(f"\nAgent: {result['reply']}")
        if result["tools_used"]:
            typer.echo(f"  [使用了: {', '.join(result['tools_used'])}]")
        typer.echo()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
    reload: bool = typer.Option(False, help="开发模式热重载"),
):
    """启动 FastAPI HTTP 服务"""
    typer.echo(f"启动 API 服务: http://{host}:{port}")
    uvicorn.run("api.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
