from nicegui import ui
import os
from loguru import logger
from mti_sites_sethstenzel_me.utils import (
    load_css,
    import_web_fonts,
    send_contact_form_email
)
from mti_sites_sethstenzel_me.pages.templates.constants import *
from mti_sites_sethstenzel_me.pages.templates.header import generate_header
from mti_sites_sethstenzel_me.pages.templates.footer import generate_footer
from mti_sites_sethstenzel_me.pages.templates.center_card import generate_center_card

page_url = '/contact'

# Get recipient email from environment variable or use default
CONTACT_RECIPIENT_EMAIL = os.getenv('CONTACT_RECIPIENT_EMAIL', 'your-email@example.com')

@ui.page(page_url)
def build_contact_page():
    ui.add_head_html(import_web_fonts())
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')

    def main_conent():
        with ui.row().classes("card-inner-row card-inner-row-content"):
            # Contact form title
            with ui.column().classes('w-full gap-4'):
                ui.label('Get in Touch').classes('text-2xl font-bold mb-2')
                ui.label('Fill out the form below and I\'ll get back to you as soon as possible.').classes('text-gray-600 mb-4')

                # Form inputs
                with ui.column().classes('w-full gap-4'):
                    name_input = ui.input(
                        label='Name',
                        placeholder='Your name'
                    ).classes('w-full').props('outlined')

                    email_input = ui.input(
                        label='Email',
                        placeholder='your.email@example.com',
                        validation={
                            'Invalid email address': lambda value: '@' in value and '.' in value.split('@')[1]
                        }
                    ).classes('w-full').props('outlined')

                    message_input = ui.textarea(
                        label='Message',
                        placeholder='Your message...'
                    ).classes('w-full').props('outlined rows=6')

                    # Status message area
                    status_label = ui.label().classes('text-sm')
                    status_label.visible = False

                    # Submit button
                    async def handle_submit():
                        # Validation
                        if not name_input.value or not name_input.value.strip():
                            logger.debug("Contact form validation failed: missing name")
                            status_label.text = 'Please enter your name'
                            status_label.classes('text-red-600')
                            status_label.visible = True
                            return

                        if not email_input.value or not email_input.value.strip():
                            logger.debug("Contact form validation failed: missing email")
                            status_label.text = 'Please enter your email'
                            status_label.classes('text-red-600')
                            status_label.visible = True
                            return

                        if '@' not in email_input.value or '.' not in email_input.value.split('@')[1]:
                            logger.debug(f"Contact form validation failed: invalid email format: {email_input.value}")
                            status_label.text = 'Please enter a valid email address'
                            status_label.classes('text-red-600')
                            status_label.visible = True
                            return

                        if not message_input.value or not message_input.value.strip():
                            logger.debug("Contact form validation failed: missing message")
                            status_label.text = 'Please enter a message'
                            status_label.classes('text-red-600')
                            status_label.visible = True
                            return

                        # Log submission attempt
                        logger.info(f"Contact form submission from {name_input.value} <{email_input.value}>")

                        # Show sending status
                        submit_button.props('loading')
                        status_label.text = 'Sending message...'
                        status_label.classes('text-blue-600')
                        status_label.visible = True

                        # Send email
                        try:
                            success, message = send_contact_form_email(
                                name=name_input.value.strip(),
                                email=email_input.value.strip(),
                                message=message_input.value.strip(),
                                recipient_email=CONTACT_RECIPIENT_EMAIL
                            )
                        except Exception as e:
                            logger.exception(f"Unexpected error sending contact form email: {e}")
                            success = False
                            message = "Unexpected error occurred"

                        # Update status
                        submit_button.props(remove='loading')

                        if success:
                            logger.success(f"Contact form email sent successfully from {email_input.value}")
                            status_label.text = 'Message sent successfully! I\'ll get back to you soon.'
                            status_label.classes('text-green-600')
                            # Clear form
                            name_input.value = ''
                            email_input.value = ''
                            message_input.value = ''
                        else:
                            logger.error(f"Failed to send contact form email: {message}")
                            status_label.text = f'Failed to send message: {message}'
                            status_label.classes('text-red-600')

                        status_label.visible = True

                    submit_button = ui.button(
                        'Send Message',
                        on_click=handle_submit
                    ).classes('bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700')

        with ui.row().classes("card-inner-row-footer"):
            ui.label('In search of the fantastic, hidden in the everyday.')

    generate_center_card(generate_header, main_conent, generate_footer, url=page_url)