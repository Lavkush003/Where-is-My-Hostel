(function () {
    "use strict";

    // Mobile navigation toggle
    var menuButton = document.getElementById("mobile-menu-button");
    var mobileMenu = document.getElementById("mobile-menu");
    var openIcon = document.getElementById("mobile-menu-icon-open");
    var closeIcon = document.getElementById("mobile-menu-icon-close");

    function setMenuState(isOpen) {
        if (!menuButton || !mobileMenu) {
            return;
        }
        mobileMenu.classList.toggle("hidden", !isOpen);
        menuButton.setAttribute("aria-expanded", String(isOpen));
        if (openIcon) {
            openIcon.classList.toggle("hidden", isOpen);
        }
        if (closeIcon) {
            closeIcon.classList.toggle("hidden", !isOpen);
        }
    }

    if (menuButton && mobileMenu) {
        menuButton.addEventListener("click", function () {
            setMenuState(mobileMenu.classList.contains("hidden"));
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth >= 1024) {
                setMenuState(false);
            }
        });
    }

    // Authenticated profile dropdown
    var profileButton = document.getElementById("profile-menu-button");
    var profileMenu = document.getElementById("profile-menu");

    function setProfileState(isOpen) {
        if (!profileButton || !profileMenu) {
            return;
        }
        profileMenu.classList.toggle("hidden", !isOpen);
        profileButton.setAttribute("aria-expanded", String(isOpen));
    }

    if (profileButton && profileMenu) {
        profileButton.addEventListener("click", function () {
            setProfileState(profileMenu.classList.contains("hidden"));
        });

        document.addEventListener("click", function (event) {
            if (
                !profileMenu.contains(event.target) &&
                !profileButton.contains(event.target)
            ) {
                setProfileState(false);
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth < 1024) {
                setProfileState(false);
            }
        });
    }

    // Accommodation Category Tabs (Inspired by Image 1)
    var categoryTabs = document.querySelectorAll("[data-category-tab]");
    var stayTypeInput = document.querySelector("[data-stay-type-input]");
    if (categoryTabs.length > 0 && stayTypeInput) {
        categoryTabs.forEach(function (tab) {
            tab.addEventListener("click", function () {
                var value = tab.getAttribute("data-category-tab");
                stayTypeInput.value = value;
                categoryTabs.forEach(function (t) {
                    t.classList.remove("bg-white", "text-brand-950", "shadow-sm");
                    t.classList.add("text-white/80", "hover:text-white", "hover:bg-white/10");
                });
                tab.classList.remove("text-white/80", "hover:text-white", "hover:bg-white/10");
                tab.classList.add("bg-white", "text-brand-950", "shadow-sm");
            });
        });
    }

    // Suggested Destinations Dropdown (Inspired by Image 4)
    var destInput = document.querySelector("[data-destination-input]");
    var destDropdown = document.querySelector("[data-destination-dropdown]");
    if (destInput && destDropdown) {
        function showDestDropdown() {
            destDropdown.classList.remove("hidden");
            destInput.setAttribute("aria-expanded", "true");
        }
        function hideDestDropdown() {
            destDropdown.classList.add("hidden");
            destInput.setAttribute("aria-expanded", "false");
        }

        destInput.addEventListener("focus", showDestDropdown);
        destInput.addEventListener("click", function (e) {
            e.stopPropagation();
            showDestDropdown();
        });

        document.querySelectorAll("[data-destination-choice]").forEach(function (choice) {
            choice.addEventListener("click", function (e) {
                e.preventDefault();
                var city = choice.getAttribute("data-city") || "";
                var query = choice.getAttribute("data-query") || city;
                destInput.value = query;
                var citySelect = document.querySelector("[data-city-select]");
                if (citySelect && city) {
                    citySelect.value = city;
                }
                hideDestDropdown();
            });
        });

        document.addEventListener("click", function (e) {
            if (!destDropdown.contains(e.target) && e.target !== destInput) {
                hideDestDropdown();
            }
        });
    }

    // Global escape key handler
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            var profileWasOpen =
                profileMenu && !profileMenu.classList.contains("hidden");
            setMenuState(false);
            setProfileState(false);
            if (destDropdown) {
                destDropdown.classList.add("hidden");
                if (destInput) {
                    destInput.setAttribute("aria-expanded", "false");
                }
            }
            if (profileWasOpen && profileButton) {
                profileButton.focus();
            }
        }
    });

    // Move-in date minimum restriction
    var moveInDate = document.querySelector("[data-move-in-date]");
    if (moveInDate) {
        var today = new Date();
        var localDate = new Date(
            today.getTime() - today.getTimezoneOffset() * 60000
        );
        moveInDate.min = localDate.toISOString().split("T")[0];
    }

    // Search submit loading feedback
    document.querySelectorAll("[data-search-form]").forEach(function (form) {
        form.addEventListener("submit", function () {
            var button = form.querySelector("[data-search-submit]");
            if (!button) {
                return;
            }

            var icon = button.querySelector("[data-search-icon]");
            var spinner = button.querySelector("[data-search-spinner]");
            var label = button.querySelector("[data-search-label]");

            button.disabled = true;
            button.classList.add("cursor-wait", "opacity-90");
            if (icon) {
                icon.classList.add("hidden");
            }
            if (spinner) {
                spinner.classList.remove("hidden");
            }
            if (label) {
                label.textContent = "Searching...";
            }
        });
    });

    // Restore search button on bfcache navigation
    window.addEventListener("pageshow", function () {
        document.querySelectorAll("[data-search-form]").forEach(function (form) {
            var button = form.querySelector("[data-search-submit]");
            if (!button) {
                return;
            }

            var icon = button.querySelector("[data-search-icon]");
            var spinner = button.querySelector("[data-search-spinner]");
            var label = button.querySelector("[data-search-label]");

            button.disabled = false;
            button.classList.remove("cursor-wait", "opacity-90");
            if (icon) {
                icon.classList.remove("hidden");
            }
            if (spinner) {
                spinner.classList.add("hidden");
            }
            if (label) {
                label.textContent = "Search stays";
            }
        });
    });

    // Confirmation dialogs
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.getAttribute("data-confirm"))) {
                event.preventDefault();
            }
        });
    });

    // Auto-update footer copyright year
    document.querySelectorAll("[data-current-year]").forEach(function (element) {
        element.textContent = String(new Date().getFullYear());
    });
})();
