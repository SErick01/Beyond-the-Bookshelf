(async () => {
  const SUPABASE_URL = "https://swfkspdirzdqotywgvop.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN3ZmtzcGRpcnpkcW90eXdndm9wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkyNDk4OTEsImV4cCI6MjA3NDgyNTg5MX0.KEH4KkXwYBFA3Frw_Yx8vXPmB2bzJwmdcFhb2Fg6dWY";
  const STORAGE_BASE = SUPABASE_URL + "/storage/v1/object/public/";
  const PLACEHOLDER = STORAGE_BASE + "cover/placeholder.jpg";
  const API_BASE = "https://beyond-the-bookshelf.onrender.com";
  const token = localStorage.getItem("btb_token");


  async function fetchCurrentUserId() {
    if (!token) return null;

    try {
      const res = await fetch(`${API_BASE}/api/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
        mode: "cors",
      });

      if (!res.ok) {
        console.warn("fetchCurrentUserId: /me", res.status);
        return null;
      }
      const me = await res.json();
      console.log("Current user from /me:", me);
      return me.user_id || me.id || null;

    } catch (err) {
      console.error("fetchCurrentUserId failed", err);
      return null;
    }
  }

  const CURRENT_USER_ID = await fetchCurrentUserId();
  console.log("CURRENT_USER_ID (view list):", CURRENT_USER_ID);

  const params = new URLSearchParams(window.location.search);
  const shelfId = params.get("shelf_id");
  const listTitle = document.getElementById("list-title");
  const bookList = document.getElementById("book-list");
  const searchInput = document.getElementById("book-search-input");

  if (!bookList) {
    console.error("No #book-list container found.");
    return;
  }

  
  async function loadShelf() {
    if (!shelfId) {
      bookList.innerHTML = `
        <p class="text-center text-gray-700">
          No list selected. Open this page with ?shelf_id=### in the URL.
        </p>`;
      return;
    }

    if (!token) {
      bookList.innerHTML = `
        <p class="text-center text-gray-700">
          Please log in to view this list.
        </p>`;
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE}/api/home/shelves/${encodeURIComponent(shelfId)}/items?limit=100`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          mode: "cors",
        }
      );

      if (res.status === 403) {
        bookList.innerHTML = `
          <p class="text-center text-gray-700">
            You don't have access to this list. Please log in as the correct user.
          </p>`;
        return;
      }

      if (res.status === 404) {
        bookList.innerHTML = `
          <p class="text-center text-gray-700">
            This list could not be found.
          </p>`;
        return;
      }

      if (!res.ok) {
        console.error("Failed to load shelf items", res.status);
        bookList.innerHTML = `
          <p class="text-center text-gray-700">
            Could not load books for this list.
          </p>`;
        return;
      }

      const data = await res.json();
      if (data.name && listTitle) {listTitle.textContent = data.name;}

      const items = data.items || [];
      if (!items.length) {
        bookList.innerHTML = `
          <p class="text-center text-gray-700">
            There are no books on this list yet.
          </p>`;
        return;
      }

      renderItems(items);
    } catch (err) {
      console.error("Error loading shelf", err);
      bookList.innerHTML = `
        <p class="text-center text-gray-700">
          Something went wrong loading this list.
        </p>`;
    }
  }


  function renderItems(items) {
    bookList.innerHTML = "";

    for (const item of items) {
      const title = item.title || "Untitled";
      const rawCover = item.cover_url || "";
      const coverUrl = rawCover
        ? (rawCover.startsWith("http")
            ? rawCover
            : STORAGE_BASE + rawCover.replace(/^\/+/, ""))
        : PLACEHOLDER;

      const card = document.createElement("div");
      card.className =
        "flex items-start p-4 border-b border-gray-400 " +
        "hover:bg-card-background/70 transition-colors cursor-pointer";
      card.dataset.title = title.toLowerCase();
      card.dataset.workId = item.work_id || "";
      card.dataset.editionId = item.edition_id || "";

      card.innerHTML = `
        <img
          src="${coverUrl}"
          alt="${title}"
          class="w-16 h-24 object-cover shadow-lg rounded-md mr-4 flex-shrink-0"
        >
        <div class="flex-grow">
          <h3 class="text-xl font-bold text-dark-brown leading-tight mb-1">
            ${title}
          </h3>
          <p class="text-gray-700 text-sm mb-2">
            <!-- TODO: author name if you want to join authors here later -->
          </p>
        </div>
      `;

      card.addEventListener("click", () => {
        const workId = card.dataset.workId;
        const editionId = card.dataset.editionId;
        let url = "View-book.html";
        const qp = new URLSearchParams();
        if (editionId) {
          qp.set("edition_id", editionId);
        } else if (workId) {
          qp.set("work_id", workId);
        }
        const queryString = qp.toString();
        if (queryString) {
          url += "?" + queryString;
        }
        window.location.href = url;
      });

      bookList.appendChild(card);
    }
  }
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.trim().toLowerCase();
      const cards = bookList.querySelectorAll("div[data-title]");
      cards.forEach((card) => {
        const title = card.dataset.title || "";
        card.style.display = !q || title.includes(q) ? "" : "none";
      });
    });
  }
  loadShelf();
})();
