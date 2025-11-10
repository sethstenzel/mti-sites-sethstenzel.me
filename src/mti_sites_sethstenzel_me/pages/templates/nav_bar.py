from nicegui import ui
import base64


def nav_bar(active_page='') -> None:
    def link(label: str, path: str, icon_path:str = '', new_tab:bool=False, encode_icon=False):
        is_active = bool(active_page == path)
        base = 'no-underline hover:underline cursor-pointer'
        active = ' active-page-link'

        if icon_path and encode_icon:
            # Convert the image to base64
            try:
                with open('.' + icon_path, 'rb') as img_file:
                    encoded = base64.b64encode(img_file.read()).decode('utf-8')

                # Guess MIME type from file extension
                ext = icon_path.split('.')[-1].lower()
                mime_type = f'image/{ext if ext != "svg" else "svg+xml"}'

                data_uri = f'data:{mime_type};base64,{encoded}'

                with ui.link(target=path, new_tab=new_tab):
                    ui.image(data_uri).props(
                        f'no-spinner no-transition loading="eager" fetchpriority="high" alt="{label.lower()}"'
                    ).classes('nav-bar-icon')
            except Exception as e:
                print(f"Error loading icon {icon_path}: {e}")
                ui.link(label, path).classes(base + (active if is_active else ''))
        elif icon_path:
            with ui.link(target=path, new_tab=new_tab):
                ui.image(f'{icon_path}').props(f'no-spinner no-transition loading="eager" fetchpriority="high" alt="{label.lower()}"').classes('nav-bar-icon')
        else:
            ui.link(label, path).classes(base + (active if is_active else ''))

    with ui.row().classes('nav-bar-links w-full text-black px-4 py-2 gap-3 items-center'):
        link('Home', '/')
        link('Portfolio', '/portfolio')
        link('Articles', '/articles')
        link('Contact', '/contact')
        link('GitHub', 'https://github.com/sethstenzel', icon_path='/static/imgs/gh.png', new_tab=True)
        link('YouTube', 'https://www.youtube.com/@sethstenzel', icon_path='/static/imgs/yt.svg', new_tab=True, encode_icon=True)