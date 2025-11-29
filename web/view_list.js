document.addEventListener("DOMContentLoaded", () => {
  const apiBase = "https://beyond-the-bookshelf.onrender.com";
  const token = localStorage.getItem("btb_token");
  const COVER_BASE =
    "https://swfkspdirzdqotywgvop.supabase.co/storage/v1/object/public/";
  const PLACEHOLDER_COVER = COVER_BASE + "cover/placeholder.jpg";

  function buildCoverUrl(relativeUrl) {
    if (!relativeUrl || typeof relativeUrl !== "string") {
      return PLACEHOLDER_COVER;
    }
    if (relativeUrl.startsWith("http://") || relativeUrl.startsWith("https://")) {
      return relativeUrl;
    }
    if (relativeUrl.startsWith("cover/")) {
      return COVER_BASE + relativeUrl;
    }
    return PLACEHOLDER_COVER;
  }

  const params = new URLSearchParams(window.location.search);
  const listType = params.get("type");
  const shelfId = params.get("shelf_id");
  const listTitleEl = document.getElementById("list-title");
  const bookListEl = document.getElementById("book-list");
  const searchInput = document.getElementById("book-search-input");
  const fabButton = document.getElementById("fab");
  const searchModal = document.getElementById("search-modal");
  const modalSearchInput = document.getElementById("modal-book-search-input");
  const closeModalButton = document.getElementById("close-modal");
  const performSearchButton = document.getElementById("perform-search");

  if (!bookListEl) {
    console.error("view-lists: #book-list not found");
    return;
  }


  async function loadList() {
    if (!token) {
      bookListEl.innerHTML =
        '<p class="text-center text-gray-700">Please log in to view this list.</p>';
      return;
    }

    if (listType === "reading") {
      await loadFromEndpoint("/api/home/reading_list?limit=100", "All current reads");

    } else if (listType === "completed") {
      await loadFromEndpoint(
        "/api/home/completed_list?limit=100",
        "All completed books"
      );

    } else if (shelfId) {
      await loadFromEndpoint(
        `/api/home/shelves/${encodeURIComponent(shelfId)}/items?limit=100`,
        null
      );

    } else {
      bookListEl.innerHTML =
        '<p class="text-center text-gray-700">No list selected.</p>';
    }
  }


  async function loadFromEndpoint(pathWithQuery, fallbackName) {
    try {
      const res = await fetch(`${apiBase}${pathWithQuery}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        mode: "cors",
      });

      if (res.status === 403) {
        bookListEl.innerHTML =
          '<p class="text-center text-gray-700">You do not have access to this list.</p>';
        return;
      }

      if (res.status === 404) {
        bookListEl.innerHTML =
          '<p class="text-center text-gray-700">This list could not be found.</p>';
        return;
      }

      if (!res.ok) {
        console.error("view-lists: failed to load list", res.status);
        bookListEl.innerHTML =
          '<p class="text-center text-gray-700">Could not load books for this list.</p>';
        return;
      }

      const data = await res.json();
      if (listTitleEl) {
        listTitleEl.textContent = data.name || fallbackName || "List";
      }

      const items = data.items || [];
      if (!items.length) {
        bookListEl.innerHTML =
          '<p class="text-center text-gray-700">There are no books in this list yet.</p>';
        return;
      }

      renderItems(items);
    } catch (err) {
      console.error("view-lists: error loading list", err);
      bookListEl.innerHTML =
        '<p class="text-center text-gray-700">Something went wrong loading this list.</p>';
    }
  }


  function renderItems(items) {
    bookListEl.innerHTML = "";

    items.forEach((item) => {
      const title = item.title || "Untitled";
      const workId = item.work_id;
      const editionId = item.edition_id;
      const coverUrl = buildCoverUrl(item.cover_url);
      const card = document.createElement("a");
      card.className =
        "flex items-start p-4 border-b border-gray-400 hover:bg-card-background/70 transition-colors cursor-pointer";
      card.href = buildViewBookUrl(workId, editionId);
      card.dataset.title = title.toLowerCase();
      card.innerHTML = `
        <img
          src="${coverUrl}"
          alt="${title}"
          class="w-16 h-24 object-cover shadow-lg rounded-md mr-4 flex-shrink-0"
          onerror="this.onerror=null;this.src='${PLACEHOLDER_COVER}'"
        >
        <div class="flex-grow">
          <h3 class="text-xl font-bold text-dark-brown leading-tight mb-1">
            ${title}
          </h3>
          <p class="text-gray-700 text-sm mb-2"></p>
        </div>
      `;

      bookListEl.appendChild(card);
    });
  }

  function buildViewBookUrl(workId, editionId) {
    let url = "View-book.html";
    const qs = new URLSearchParams();

    if (editionId) {
      qs.set("edition_id", editionId);
    } else if (workId) {
      qs.set("work_id", workId);
    }
    const q = qs.toString();
    if (q) url += "?" + q;
    return url;
  }

  function filterBooks() {
    const q = (searchInput?.value || "").trim().toLowerCase();
    const cards = bookListEl.querySelectorAll("a");
    cards.forEach((card) => {
      const title = card.dataset.title || "";
      card.style.display = !q || title.includes(q) ? "" : "none";
    });
  }

  if (searchInput) {searchInput.addEventListener("input", filterBooks);}

  if (fabButton && searchModal) {
    fabButton.addEventListener("click", () => {
      searchModal.classList.remove("hidden");
      if (modalSearchInput) {
        modalSearchInput.value = "";
        modalSearchInput.focus();
      }
    });
  }

  if (closeModalButton && searchModal) {
    closeModalButton.addEventListener("click", () => {
      searchModal.classList.add("hidden");
    });
  }

  if (performSearchButton && searchModal) {
    performSearchButton.addEventListener("click", () => {
      searchModal.classList.add("hidden");
    });
  }
  loadList();
});
