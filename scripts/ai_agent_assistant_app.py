import gradio as gr
from ai_agent_assistant_libs import (
    chat,
    handle_refresh,
    stop_chatbot,
    handle_feedback,
    refresh_system_message
)

# Gather calendar events
refresh_system_message()

# ⏺️ Main app
with gr.Blocks() as demo:
    gr.Markdown("## 🧠 Smart Scheduler")

    chatbot = gr.Chatbot()
    user_input = gr.Textbox(
        placeholder="How can I help you with your calendar?",
        show_label=False
    )

    feedback_buttons = gr.Radio(
        choices=["👍 Yes", "👎 No", "💬 Suggest Improvement"],
        label="Did that work as expected?",
        visible=False
    )

    feedback_state = gr.State({"awaiting": False, "last_action": None, "context": None})
    chat_history = gr.State([])

    with gr.Row():
        refresh_btn = gr.Button("🔄 Refresh Calendar")
        close_btn = gr.Button("🛑 Exit Assistant")

    # Handle user message
    def handle_user_input(message, history, feedback_state):
        history, updated_feedback = chat(message, history, feedback_state)
        return history, updated_feedback, gr.update(visible=updated_feedback["awaiting"]), ""

    user_input.submit(
        fn=handle_user_input,
        inputs=[user_input, chat_history, feedback_state],
        outputs=[chatbot, feedback_state, feedback_buttons, user_input],
        queue=False
    )

    # Handle feedback
    feedback_buttons.change(
        fn=handle_feedback,
        inputs=[feedback_buttons, feedback_state, chat_history],
        outputs=[chatbot, feedback_state, feedback_buttons]
    )

    # Refresh calendar
    refresh_btn.click(
        fn=handle_refresh,
        inputs=[chat_history],
        outputs=[chatbot]
    )

    # Exit assistant
    close_btn.click(
        fn=stop_chatbot,
        inputs=[chat_history],
        outputs=[chatbot]
    )

demo.launch(inbrowser=True)
