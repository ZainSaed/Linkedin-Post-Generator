import os
import json
import time
import secrets
import hashlib
import hmac
from pathlib import Path
from urllib.parse import urlencode

import requests
import streamlit as st
from dotenv import load_dotenv

from backend import graph


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent

AUTH_FILE = (
    BASE_DIR / ".linkedin_auth.json"
)

OAUTH_STATE_FILE = (
    BASE_DIR / ".linkedin_oauth_state"
)


LINKEDIN_CLIENT_ID = os.getenv(
    "LINKEDIN_CLIENT_ID"
)

LINKEDIN_CLIENT_SECRET = os.getenv(
    "LINKEDIN_CLIENT_SECRET"
)

LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI",
)


st.set_page_config(
    page_title="AI LinkedIn Post Generator",
    page_icon="LI",
    layout="wide",
)


def linkedin_configured():
    return bool(
        LINKEDIN_CLIENT_ID
        and LINKEDIN_CLIENT_SECRET
        and LINKEDIN_REDIRECT_URI
    )


def load_auth():
    if not AUTH_FILE.exists():
        return {}

    try:
        with open(
            AUTH_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return {}


def save_auth(data):
    temporary_file = AUTH_FILE.with_suffix(
        ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
        )

    temporary_file.replace(
        AUTH_FILE
    )


def save_oauth_state(state):
    data = {
        "state": state,
        "created": int(time.time()),
    }

    temporary_file = (
        OAUTH_STATE_FILE.with_suffix(".tmp")
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
        )

    temporary_file.replace(
        OAUTH_STATE_FILE
    )


def load_oauth_state():
    if not OAUTH_STATE_FILE.exists():
        return None

    try:
        with open(
            OAUTH_STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return None


def delete_oauth_state():
    try:
        if OAUTH_STATE_FILE.exists():
            OAUTH_STATE_FILE.unlink()

    except Exception:
        pass


def create_oauth_state():
    state = secrets.token_urlsafe(32)

    save_oauth_state(
        state
    )

    return state


def verify_oauth_state(
    returned_state,
):
    saved = load_oauth_state()

    if not saved:
        return False

    original_state = saved.get(
        "state"
    )

    created = saved.get(
        "created"
    )

    if not original_state or not created:
        return False

    if time.time() - created > 600:
        delete_oauth_state()
        return False

    valid = hmac.compare_digest(
        str(original_state),
        str(returned_state or ""),
    )

    if valid:
        delete_oauth_state()

    return valid


def create_linkedin_login_url():
    if not linkedin_configured():
        raise RuntimeError(
            "LinkedIn configuration is missing."
        )

    state = create_oauth_state()

    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": (
            "openid profile w_member_social"
        ),
    }

    return (
        "https://www.linkedin.com/oauth/v2/"
        "authorization?"
        + urlencode(params)
    )


def exchange_code_for_token(
    code,
):
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":
                "authorization_code",
            "code":
                code,
            "client_id":
                LINKEDIN_CLIENT_ID,
            "client_secret":
                LINKEDIN_CLIENT_SECRET,
            "redirect_uri":
                LINKEDIN_REDIRECT_URI,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            "LinkedIn token exchange failed:\n"
            + response.text
        )

    data = response.json()

    if not data.get(
        "access_token"
    ):
        raise RuntimeError(
            "LinkedIn did not return an access token."
        )

    return data


def get_linkedin_profile(
    access_token,
):
    response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            "Authorization":
                f"Bearer {access_token}"
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            "LinkedIn profile request failed:\n"
            + response.text
        )

    profile = response.json()

    if not profile.get("sub"):
        raise RuntimeError(
            "LinkedIn member ID was not returned."
        )

    return profile


def save_linkedin_connection(
    token_data,
    profile,
):
    data = load_auth()

    data["access_token"] = (
        token_data["access_token"]
    )

    data["profile"] = profile

    if token_data.get(
        "expires_in"
    ):
        data["expires_at"] = (
            int(time.time())
            + int(
                token_data["expires_in"]
            )
        )

    if token_data.get(
        "refresh_token"
    ):
        data["refresh_token"] = (
            token_data["refresh_token"]
        )

    save_auth(data)


def get_linkedin_connection():
    data = load_auth()

    access_token = data.get(
        "access_token"
    )

    profile = data.get(
        "profile"
    )

    if not access_token or not profile:
        return None

    expires_at = data.get(
        "expires_at"
    )

    if expires_at:
        if time.time() >= expires_at:
            return None

    return {
        "access_token": access_token,
        "profile": profile,
    }


def publish_to_linkedin(
    access_token,
    member_id,
    text,
):
    if not access_token:
        raise RuntimeError(
            "LinkedIn access token is missing."
        )

    if not member_id:
        raise RuntimeError(
            "LinkedIn member ID is missing."
        )

    payload = {
        "author":
            f"urn:li:person:{member_id}",
        "commentary":
            text.strip(),
        "visibility":
            "PUBLIC",
        "distribution": {
            "feedDistribution":
                "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState":
            "PUBLISHED",
        "isReshareDisabledByAuthor":
            False,
    }

    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization":
                f"Bearer {access_token}",
            "Content-Type":
                "application/json",
            "X-Restli-Protocol-Version":
                "2.0.0",
            "Linkedin-Version":
                "202606",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code == 401:
        raise RuntimeError(
            "LinkedIn access token is expired "
            "or invalid. Reconnect LinkedIn."
        )

    if response.status_code == 403:
        raise RuntimeError(
            "LinkedIn rejected the request. "
            "Check your application's permissions."
        )

    if not response.ok:
        raise RuntimeError(
            "LinkedIn publishing failed:\n"
            f"Status: {response.status_code}\n"
            f"{response.text}"
        )

    return response.headers.get(
        "x-restli-id",
        "published",
    )


def handle_oauth_callback():
    if "error" in st.query_params:

        error = st.query_params.get(
            "error"
        )

        description = st.query_params.get(
            "error_description",
            "",
        )

        delete_oauth_state()

        st.error(
            "LinkedIn authorisation failed."
        )

        st.code(
            f"{error}\n\n{description}"
        )

        st.query_params.clear()

        return True

    if "code" not in st.query_params:
        return False

    code = st.query_params.get(
        "code"
    )

    state = st.query_params.get(
        "state"
    )

    if not verify_oauth_state(
        state
    ):

        st.error(
            "Invalid OAuth state. "
            "Please click Connect LinkedIn again."
        )

        st.query_params.clear()

        return True

    try:

        with st.spinner(
            "Connecting LinkedIn..."
        ):

            token_data = (
                exchange_code_for_token(
                    code
                )
            )

            profile = get_linkedin_profile(
                token_data[
                    "access_token"
                ]
            )

            save_linkedin_connection(
                token_data,
                profile,
            )

        st.query_params.clear()

        st.session_state.linkedin_connected = True

        st.success(
            "LinkedIn connected successfully."
        )

        st.rerun()

    except Exception as error:

        st.error(
            "LinkedIn connection failed."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(error)
            )

        st.query_params.clear()

    return True


if "topic" not in st.session_state:
    st.session_state.topic = ""

if "generated_post" not in st.session_state:
    st.session_state.generated_post = None

if "research" not in st.session_state:
    st.session_state.research = None

if "generation_error" not in st.session_state:
    st.session_state.generation_error = None

if "human_decision" not in st.session_state:
    st.session_state.human_decision = None

if "published_id" not in st.session_state:
    st.session_state.published_id = None

if "linkedin_connected" not in st.session_state:
    st.session_state.linkedin_connected = False


handle_oauth_callback()


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1050px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    .hero {
        margin-bottom: 2rem;
    }

    .hero h1 {
        font-size: 2.7rem;
        margin-bottom: 0.3rem;
    }

    .hero p {
        color: #666;
        font-size: 1.05rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="hero">
        <h1>AI LinkedIn Post Generator</h1>
        <p>
            Research. Generate. Review. Publish when you approve.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


st.subheader(
    "Create your post"
)


topic = st.text_input(
    "Topic",
    value=st.session_state.topic,
    placeholder=(
        "What do you want to write about?"
    ),
)


if st.button(
    "Generate Post",
    type="primary",
    use_container_width=True,
):

    if not topic.strip():

        st.warning(
            "Please enter a topic."
        )

    else:

        st.session_state.topic = (
            topic.strip()
        )

        st.session_state.generated_post = None
        st.session_state.research = None
        st.session_state.generation_error = None
        st.session_state.human_decision = None

        try:

            thread_id = (
                "post-"
                + secrets.token_urlsafe(16)
            )

            with st.status(
                "Generating post...",
                expanded=True,
            ) as status:

                st.write(
                    "Researching topic..."
                )

                result = graph.invoke(
                    {
                        "topic":
                            topic.strip()
                    },
                    config={
                        "configurable": {
                            "thread_id":
                                thread_id
                        }
                    },
                )

                if result.get(
                    "error"
                ):
                    raise RuntimeError(
                        result["error"]
                    )

                st.write(
                    "Generating LinkedIn content..."
                )

                st.session_state.research = (
                    result.get(
                        "research"
                    )
                )

                st.session_state.generated_post = (
                    result.get(
                        "post"
                    )
                )

                if not st.session_state.generated_post:
                    raise RuntimeError(
                        "No post was generated."
                    )

                status.update(
                    label="Post generated",
                    state="complete",
                )

        except Exception as error:

            st.session_state.generation_error = (
                str(error)
            )


if st.session_state.generation_error:

    st.error(
        "Post generation failed."
    )

    with st.expander(
        "Technical details"
    ):
        st.code(
            st.session_state.generation_error
        )


if st.session_state.generated_post:

    st.divider()

    st.subheader(
        "Review your post"
    )

    edited_post = st.text_area(
        "Post content",
        value=st.session_state.generated_post,
        height=500,
    )

    st.caption(
        f"{len(edited_post)} characters"
    )

    with st.expander(
        "Preview"
    ):
        st.markdown(
            edited_post
        )

    if st.session_state.research:

        with st.expander(
            "Research used"
        ):
            st.write(
                st.session_state.research
            )

    st.divider()

    if st.session_state.human_decision is None:

        st.subheader(
            "Human approval"
        )

        st.info(
            "This post has NOT been published."
        )

        st.write(
            "Do you want to publish it on LinkedIn?"
        )

        yes_col, no_col = st.columns(2)

        with yes_col:

            if st.button(
                "Yes, publish",
                type="primary",
                use_container_width=True,
            ):

                st.session_state.generated_post = (
                    edited_post
                )

                st.session_state.human_decision = (
                    "yes"
                )

                st.rerun()

        with no_col:

            if st.button(
                "No, keep as draft",
                use_container_width=True,
            ):

                st.session_state.generated_post = (
                    edited_post
                )

                st.session_state.human_decision = (
                    "no"
                )

                st.rerun()


    elif st.session_state.human_decision == "no":

        st.success(
            "Saved as a draft. Nothing was published."
        )

        st.text_area(
            "Draft",
            value=edited_post,
            height=400,
            key="draft_output",
        )

        if st.button(
            "Create another post",
            use_container_width=True,
        ):

            st.session_state.topic = ""
            st.session_state.generated_post = None
            st.session_state.research = None
            st.session_state.human_decision = None

            st.rerun()


    elif st.session_state.human_decision == "yes":

        st.subheader(
            "Publish to LinkedIn"
        )

        connection = (
            get_linkedin_connection()
        )

        if not connection:

            st.info(
                "You approved the post. "
                "Connect LinkedIn to continue."
            )

            if not linkedin_configured():

                st.error(
                    "LinkedIn OAuth is not configured."
                )

                st.code(
                    "LINKEDIN_CLIENT_ID\n"
                    "LINKEDIN_CLIENT_SECRET\n"
                    "LINKEDIN_REDIRECT_URI"
                )

            else:

                login_url = (
                    create_linkedin_login_url()
                )

                st.link_button(
                    "Connect LinkedIn",
                    login_url,
                    use_container_width=True,
                )

        else:

            profile = connection[
                "profile"
            ]

            name = profile.get(
                "name",
                "LinkedIn Member",
            )

            st.success(
                f"Connected as {name}"
            )

            st.warning(
                "The post will only be published "
                "after you click Publish Now."
            )

            if st.button(
                "Publish Now",
                type="primary",
                use_container_width=True,
            ):

                try:

                    post_id = publish_to_linkedin(
                        connection[
                            "access_token"
                        ],
                        profile.get("sub"),
                        edited_post,
                    )

                    st.session_state.published_id = (
                        post_id
                    )

                    st.session_state.topic = ""
                    st.session_state.generated_post = None
                    st.session_state.research = None
                    st.session_state.human_decision = None

                    st.success(
                        "Published successfully to LinkedIn."
                    )

                except Exception as error:

                    st.error(
                        "Publishing failed."
                    )

                    with st.expander(
                        "Technical details"
                    ):
                        st.code(
                            str(error)
                        )


if st.session_state.published_id:

    st.divider()

    st.success(
        "Your LinkedIn post was published successfully."
    )

    st.caption(
        f"Post ID: {st.session_state.published_id}"
    )