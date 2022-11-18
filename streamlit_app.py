import re
import time
from dataclasses import dataclass
from datetime import datetime

import httpx
import pypistats
import requests
import streamlit as st
from bs4 import BeautifulSoup
from markdownlit import mdlit
from stqdm import stqdm

st.set_page_config("Streamlit Components Hub", "🎪", layout="wide")
NUM_COLS = 4

EXCLUDE = [
    "streamlit",
    "streamlit-nightly",
    "streamlit-fesion",
    "streamlit-aggrid-pro",
    "st-dbscan",
    "st-kickoff",
    "st-undetected-chromedriver",
    "st-package-reviewer",
    "streamlit-webcam-example",
    "st-pyv8",
    "streamlit-extras-arnaudmiribel",
    "st-schema-python",
    "st-optics",
    "st-spin",
    "st-dataprovider",
    "st-microservice",
    "st_nester",
    "st-jsme",
    "st-parsetree",
    "st-git-hooks",
    "st-schema",
    "st-distributions",
    "st-common-data",
    "awesome-streamlit",
    "awesome-streamlit-master",
]


def icon(emoji: str):
    """Shows an emoji as a Notion-style page icon."""
    st.write(
        f'<span style="font-size: 78px; line-height: 1">{emoji}</span>',
        unsafe_allow_html=True,
    )


st.write(
    '<style>[data-testid="stImage"] img {border: 1px solid #D6D6D9; border-radius: 3px; height: 200px; object-fit: cover; width: 100%} .block-container img:hover {}</style>',
    unsafe_allow_html=True,
)

# st.write(
#     "<style>.block-container img {border: 1px solid #D6D6D9; border-radius: 3px; width: 100%; height: 200px; position: absolute; top: 50%; left: 50%;transform: translate(-50%, -50%);} .block-container img:hover {}</style>",
#     unsafe_allow_html=True,
# )

icon("🎪")
"""
# Streamlit Components Hub
"""
description = st.empty()
# col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
col1, col2, col3 = st.columns([2, 1, 1])
# with col1:
# search = st_keyup("Search", debounce=200)
search = col1.text_input("Search", placeholder='e.g. "image" or "text" or "card"')
sorting = col2.selectbox("Sort", ["⭐️ Stars", "⬇️ Downloads last month", "🐣 Newest"])
package_manager = col3.selectbox("Install via", ["pip", "pipenv", "poetry"])
# col4.write("")
# col4.write("")
# if col4.button("♻️ Update packages"):
#    st.experimental_memo.clear()
if package_manager == "pip" or package_manager == "pipenv":
    install_command = package_manager + " install"
elif package_manager == "poetry":
    install_command = "poetry add"
# with col2:
#     st.selectbox("Sort by", ["Github stars", "Newest"], disabled=True)
st.write("")
st.write("")


@st.experimental_memo(ttl=28 * 24 * 3600, persist="disk", show_spinner=False)
def get(*args, **kwargs):
    res = requests.get(*args, **kwargs)
    return res.status_code, res.text


@st.experimental_memo(ttl=28 * 24 * 3600, persist="disk", show_spinner=False)
def get_github_info(url):
    """use the github api to get the number of stars for a given repo"""
    url = url.replace("https://", "").replace("http://", "")
    user, repo = url.split("/")[1:3]
    response = requests.get(
        f"https://api.github.com/repos/{user}/{repo}",
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Token {st.secrets.gh_token}",
        },
    )
    if response.status_code == 404:
        return None, None, None, None
    elif response.status_code != 200:
        raise RuntimeError(
            f"Couldn't get repo details, status code {response.status_code} for url: {url}, user: {user}, repo: {repo}"
        )
    response_json = response.json()
    created_at = datetime.strptime(response_json["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    return (
        response_json["stargazers_count"],
        response_json["description"],
        response_json["owner"]["avatar_url"],
        created_at,
    )


@st.experimental_memo(ttl=28 * 24 * 3600, persist="disk", show_spinner=False)
def parse_github_readme(url):
    """get the image url from the github readme"""
    # TODO: Could do this by getting the raw readme file and not the rendered page.
    status_code, text = get(url)
    if status_code == 404:
        return None, None, None
    elif status_code != 200:
        raise RuntimeError(
            f"Couldn't get Github page, status code {status_code} for url: {url}"
        )
    time.sleep(0.2)  # wait a bit to not get rate limited
    soup = BeautifulSoup(text, "html.parser")
    # st.expander("Show HTML").code(response.text)
    readme = soup.find(id="readme")
    if readme is None:
        return None, None, None

    # Find first image that's not a badge or logo.
    images = readme.find_all("img")

    def is_no_badge(img):
        srcs = img["src"] + img.get("data-canonical-src", "")
        return not (
            "badge" in srcs
            or "shields.io" in srcs
            or "circleci" in srcs
            or "buymeacoffee" in srcs
            or "ko-fi" in srcs
            or "logo" in srcs
            or "streamlit-mark" in srcs
            or "coverage" in srcs
            or "Cover" in srcs
        )

    images = list(filter(is_no_badge, images))
    if not images:
        image_url = None
    else:
        image_url = images[0]["src"]
        if image_url.startswith("/"):
            image_url = "https://github.com" + image_url

    # Find text in first paragraph.
    description = None
    paragraphs = readme.find_all("p")
    for paragraph in paragraphs:
        clean_paragraph = paragraph.text.replace("\n", "").strip()
        if clean_paragraph:
            description = clean_paragraph
            break

    # Find link to demo app.
    # TODO: Should only do this if demo app is not known yet.
    try:
        demo_url = soup.find("a", href=re.compile("share\.streamlit\.io/+"))["href"]
    except TypeError:
        try:
            demo_url = soup.find("a", href=re.compile("\.streamlitapp\.com"))["href"]
        except TypeError:
            demo_url = None

    # print("func", image_url, description)
    return image_url, description, demo_url


# async def _save_screenshot(
#     url: str, img_path: str, sleep: int = 5, width: int = 1024, height: int = 576
# ) -> None:
#     browser = await pyppeteer.launch(
#         {"args": ["--no-sandbox"]},
#         handleSIGINT=False,
#         handleSIGTERM=False,
#         handleSIGHUP=False,
#     )
#     page = await browser.newPage()
#     await page.goto(url, {"timeout": 6000})  # increase timeout to 60 s for heroku apps
#     await page.emulate({"viewport": {"width": width, "height": height}})
#     time.sleep(sleep)
#     # Type (PNG or JPEG) will be inferred from file ending.
#     await page.screenshot({"path": img_path})
#     await browser.close()


# def save_screenshot(
#     url: str, img_path: str, sleep: int = 5, width: int = 1024, height: int = 576
# ):
#     asyncio.run(
#         _save_screenshot(
#             url=url, img_path=img_path, sleep=sleep, width=width, height=height
#         )
#     )


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


TRACKER = "https://discuss.streamlit.io/t/streamlit-components-community-tracker/4634"


@dataclass
class Component:
    name: str = None
    package: str = None
    demo: str = None
    forum_post: str = None
    github: str = None
    pypi: str = None
    image_url: str = None
    # screenshot_url: str = None
    stars: int = None
    github_description: str = None
    pypi_description: str = None
    avatar: str = None
    search_text: str = None
    github_author: str = None
    pypi_author: str = None
    created_at: datetime = None
    downloads: int = None


@st.experimental_memo(ttl=28 * 24 * 3600, persist="disk", show_spinner=False)
def get_all_packages():
    url = "https://pypi.org/simple/"
    status_code, text = get(url)
    soup = BeautifulSoup(text, "html.parser")
    packages = [
        a.text
        for a in soup.find_all("a")
        if (
            "streamlit" in a.text
            or a.text.startswith("st-")
            or a.text.startswith("st_")
        )
        and a.text not in EXCLUDE
    ]
    return packages


@st.experimental_memo(ttl=24 * 3600, persist="disk", show_spinner=False)
def get_downloads(package):
    try:
        downloads = pypistats.recent(package, "month", format="pandas")["last_month"][
            0
        ]  # .iloc[-1]["downloads"]
    except httpx.HTTPStatusError:
        time.sleep(10)
        downloads = pypistats.recent(package, "month", format="pandas")["last_month"][
            0
        ]  # .iloc[-1]["downloads"]
    time.sleep(0.1)  # don't get rate-limited
    return downloads


@st.experimental_memo(ttl=28 * 24 * 3600, show_spinner=False)
def get_components():
    components_dict = {}

    # Step 1: Get components from tracker
    status_code, text = get(TRACKER)
    if status_code != 200:
        raise RuntimeError(
            f"Could not access components tracker, status code {status_code}"
        )

    soup = BeautifulSoup(text, "html.parser")
    lis = soup.find_all("ul")[3].find_all("li")

    for li in stqdm(lis, desc="🎈 Crawling Streamlit forum (step 1/4)"):

        c = Component()
        name = re.sub("\(.*?\)", "", li.text)
        name = name.split(" – ")[0]
        name = name.strip()
        c.name = name

        links = [a.get("href") for a in li.find_all("a")]
        for l in links:
            if l.startswith("https://github.com"):
                c.github = l
            elif l.startswith("https://share.streamlit.io") or "streamlitapp.com" in l:
                c.demo = l
            elif l.startswith("https://discuss.streamlit.io"):
                c.forum_post = l
            elif l.startswith("https://pypi.org"):
                c.pypi = l
                c.package = re.match("https://pypi.org/project/(.*?)/", l).group(1)

        if c.github and not c.package:
            repo_name = (
                c.github.replace("https://", "").replace("http://", "").split("/")[2]
            )
            # print(repo_name)
            url = f"https://pypi.org/project/{repo_name}/"
            status_code, text = get(url)
            if status_code != 404:
                c.package = repo_name
                c.pypi = url
                # print("found package based on repo name:", repo_name)

        if c.package:
            components_dict[c.package] = c
        else:
            components_dict[c.name] = c

    # Step 2: Download PyPI index
    with st.spinner("⬇️ Downloading PyPI index (step 2/4)"):
        packages = get_all_packages()

    # Step 3: Search through PyPI packages
    # TODO: This could be wrapped in memo as well.
    for p in stqdm(packages, desc="📦 Crawling PyPI (step 3/4)"):
        # if p.startswith("streamlit") or p.startswith("st-") or p.startswith("st_"):

        # TODO: There's a JSON API to do this: https://pypi.org/pypi/<package>/json

        url = f"https://pypi.org/project/{p}/"
        status_code, text = get(url)
        if status_code != 404:
            # st.expander("show html").code(res.text)

            if not p in components_dict:
                components_dict[p] = Component(name=p)
            c = components_dict[p]

            if not c.package:
                c.package = p
            if not c.pypi:
                c.pypi = url

            if not c.pypi_author or not c.github:
                soup = BeautifulSoup(text, "html.parser")

                if not c.pypi_author:
                    pypi_author = soup.find(
                        "span", class_="sidebar-section__user-gravatar-text"
                    ).text.strip()
                    c.pypi_author = pypi_author

                if not c.github:
                    homepage = soup.find("i", class_="fas fa-home")
                    if homepage and "github.com" in homepage.parent["href"]:
                        c.github = homepage.parent["href"]
                        # print("found github link from homepage link:", c.github)
                    else:
                        sidebar_links = soup.find_all(
                            "a",
                            class_="vertical-tabs__tab vertical-tabs__tab--with-icon vertical-tabs__tab--condensed",
                        )
                        for l in sidebar_links:
                            if "github.com" in l["href"]:
                                c.github = l["href"]
                                # print(
                                #     "found github link from sidebar link:",
                                #     c.github,
                                # )
                                break

                # TODO: Maybe do this outside of the if?
                summary = soup.find("p", class_="package-description__summary")
                if (
                    summary
                    and summary.text
                    and summary.text != "No project description provided"
                ):
                    # print("found summary description on pypi:", summary.text)
                    c.pypi_description = summary.text
                else:
                    # Search for first non-empty paragraph.
                    project_description = soup.find("div", class_="project-description")
                    if project_description:
                        paragraphs = project_description.find_all("p")
                        for p in paragraphs:
                            text = p.text.replace("\n", "").strip()
                            if text:
                                c.pypi_description = text
                                break

    # Step 4: Enrich info of components found above by reading data from Github
    for c in stqdm(components_dict.values(), desc="👾 Crawling Github (step 4/4)"):

        # Try to get Github URL by combining PyPI author name + package name.
        if not c.github and c.package and c.pypi_author:
            possible_repo_names = [c.package]
            if "-" in c.package:
                # Sometimes, package names contain "-"" but repos "_", so check for these
                # mutations as well.
                possible_repo_names.append(c.package.replace("-", "_"))
            for repo in possible_repo_names:
                status_code, text = get(
                    f"https://api.github.com/repos/{c.pypi_author}/{repo}",
                    headers={
                        "Accept": "application/vnd.github.v3+json",
                        "Authorization": f"Token {st.secrets.gh_token}",
                    },
                )
                if status_code == 200:
                    c.github = f"https://github.com/{c.pypi_author}/{repo}"
                    if repo != c.package:
                        print(
                            f"found github url by mutating package name, original: {c.package}, mutated: {repo}"
                        )
                    break

        if c.github:
            # print(c.github)
            c.github_author = re.search("github.com/(.*?)/", c.github).group(1)
            try:
                (
                    c.stars,
                    c.github_description,
                    c.avatar,
                    c.created_at,
                ) = get_github_info(c.github)
            except:
                pass  # TODO: Handle this better. Sometimes Github shows 401 errors.

            # this can also return None!
            c.image_url, readme_description, demo_url = parse_github_readme(c.github)
            if not c.github_description and readme_description:
                # print("found description in github readme")
                c.github_description = readme_description
            if not c.demo and demo_url:
                # print("found demo url in github readme", demo_url)
                c.demo = demo_url

        # Get download numbers from PyPI
        if c.package:
            c.downloads = get_downloads(c.package)

        c.search_text = (
            str(c.name)
            + str(c.github_description)
            + str(c.pypi_description)
            + str(c.github_author)
            + str(c.package)
        )

    return list(components_dict.values())


@st.experimental_memo(show_spinner=False)
def sort_components(components: list, by):
    if by == "⭐️ Stars":
        return sorted(
            components,
            key=lambda c: (
                c.stars if c.stars is not None else 0,
                c.image_url is not None,  # items with image first
            ),
            reverse=True,
        )
    elif by == "🐣 Newest":
        # TODO: This only works for components that have a Github link because we pull
        # the created_at date from Github. Make this work with the release date on PyPI.
        return sorted(
            components,
            key=lambda c: (
                c.created_at if c.created_at is not None else datetime(1970, 1, 1),
                c.image_url is not None,  # items with image first
            ),
            reverse=True,
        )
    elif by == "⬇️ Downloads last month":
        return sorted(
            components,
            key=lambda c: (
                c.downloads if c.downloads is not None else 0,
                c.image_url is not None,  # items with image first
            ),
            reverse=True,
        )
    else:
        raise ValueError("`by` must be either 'Stars' or 'Newest'")


# Can't memo-ize this right now because st.image doesn't work.
# @st.experimental_memo
def show_components(components, search, limit=None):
    if search:
        components_to_show = list(
            filter(lambda c: search.lower() in c.search_text, components)
        )
    else:
        components_to_show = components

    if limit is not None:
        components_to_show = components_to_show[:limit]

    for components_chunk in chunks(components_to_show, NUM_COLS):
        cols = st.columns(NUM_COLS, gap="medium")
        for c, col in zip(components_chunk, cols):
            with col:
                if c.image_url is not None:
                    img_path = c.image_url
                # TODO: This doesn't work on Cloud, disabling for now.
                # elif c.demo is not None:
                #     screenshot_dir = Path("screenshots")
                #     screenshot_dir.mkdir(exist_ok=True, parents=True)
                #     escaped_screenshot_url = (
                #         c.demo.replace("https://", "")
                #         .replace("/", "_")
                #         .replace(".", "_")
                #     )
                #     img_path = screenshot_dir / f"{escaped_screenshot_url}.png"
                #     if not img_path.exists():
                #         save_screenshot(c.demo, img_path, sleep=15)
                else:
                    img_path = "default_image.png"

                st.image(str(img_path), use_column_width=True)
                title = f"#### {c.name}"
                if c.stars:
                    title += f" ({c.stars} ⭐️)"
                # print(title)
                st.write(title)
                if c.avatar:
                    avatar_path = c.avatar
                else:
                    # TODO: Need to use web URL because we can't expose image through static folder.
                    avatar_path = "https://icon-library.com/images/default-profile-icon/default-profile-icon-16.jpg"
                if c.github_author and c.avatar:
                    st.caption(
                        f'<a href="https://github.com/{c.github_author}"><img src="{avatar_path}" style="border: 1px solid #D6D6D9; width: 20px; height: 20px; border-radius: 50%"></a> &nbsp; <a href="https://github.com/{c.github_author}" style="color: inherit; text-decoration: inherit">{c.github_author}</a>',
                        unsafe_allow_html=True,
                    )
                # elif c.github_author:
                #     # TODO: Some of the Github pages extracted above return 404, so
                #     # we can't get the avatar image from them. We could get them by
                #     # querying with the author name directly but for now I'm just hiding the avatar images.
                #     st.caption(
                #         f'<a href="https://github.com/{c.github_author}" style="color: inherit; text-decoration: inherit">{c.github_author}</a>',
                #         unsafe_allow_html=True,
                #     )
                elif c.pypi_author:
                    st.caption(
                        f'<a href="https://pypi.org/user/{c.pypi_author}"><img src="{avatar_path}" style="border: 1px solid #D6D6D9; width: 20px; height: 20px; border-radius: 50%"></a> &nbsp; <a href="https://pypi.org/user/{c.pypi_author}" style="color: inherit; text-decoration: inherit">{c.pypi_author}</a>',
                        unsafe_allow_html=True,
                    )

                if c.github_description:
                    st.write(c.github_description)
                elif c.pypi_description:
                    st.write(c.pypi_description)
                if c.package:
                    st.code(f"{install_command} {c.package}", None)
                formatted_links = []
                if c.github:
                    # formatted_links.append(mention("Github", c.github, icon="github", write=False))
                    # formatted_links.append(f"[GitHub]({c.github})")
                    formatted_links.append(f"@(GitHub)({c.github})")
                if c.demo:
                    # formatted_links.append(mention("Demo", c.demo, icon="🎈", write=False))
                    # formatted_links.append(f"[Demo]({c.demo})")
                    formatted_links.append(f"@(🎈)(Demo)({c.demo})")
                if c.forum_post:
                    # formatted_links.append(f"[Forum]({c.forum_post})")
                    # formatted_links.append(mention("Forum", c.forum_post, icon="streamlit", write=False))
                    formatted_links.append(f"@(Forum)({c.forum_post})")
                if c.pypi:
                    # formatted_links.append(f"[PyPI]({c.pypi})")
                    # formatted_links.append(mention("PyPI", c.pypi, icon="📦", write=False))
                    formatted_links.append(f"@(📦)(PyPI)({c.pypi})")

                # st.write(" • ".join(formatted_links), unsafe_allow_html=True)
                mdlit(" &nbsp;•&nbsp; ".join(formatted_links))
        st.write("---")


components = get_components()
description.write(
    f"""
Discover {len(components)} Streamlit components!
All information on this page is automatically crawled from Github, PyPI, 
and the [Streamlit forum](https://discuss.streamlit.io/t/streamlit-components-community-tracker/4634).
"""
)
if "limit" not in st.session_state:
    st.session_state["limit"] = 100


def show_more():
    st.session_state["limit"] += 50


components = sort_components(components, sorting)
show_components(components, search, st.session_state["limit"])

if len(components) > st.session_state["limit"]:
    st.button("Show more", on_click=show_more)

# cols = st.columns(5)
# for page in range(1, 1+ math.ceil(len(components) / 100)):
#     print(page)
#     cols[page - 1].button(f"Page {page}", on_click=set_page, args=(page,))

# downloads = pypistats.recent("streamlit-image-select", "month", format="pandas")["last_month"][0]#.iloc[-1]["downloads"]
# st.write(downloads)

# status_code, text = get("https://pypi.org/project/st-searchbar/")
# soup = BeautifulSoup(text, "html.parser")
# summary = soup.find("p", class_="package-description__summary")
# if summary and summary.text and summary.text != "No project description provided":
#     print("found summary description on pypi:", summary.text)
# print(summary)
