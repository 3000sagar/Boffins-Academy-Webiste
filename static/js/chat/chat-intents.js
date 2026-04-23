window.ChatIntent = (() => {
  /**
   * detect — client-side intent detection from raw user text.
   *
   * All paths use trailing slashes to match Django canonical URLs.
   * This prevents 301 redirects that strip page CSS/JS.
   *
   * /success-stories was removed — it doesn't exist as a Django route.
   * Those keywords now correctly point to /placements/ where success
   * stories and alumni content actually lives.
   */
  function detect(text) {
    const msg = text.toLowerCase();

    // ── Courses ──────────────────────────────────────────────
    if (
      msg.includes("open courses") ||
      msg.includes("go to courses") ||
      msg.includes("courses") ||
      msg.includes("course") ||
      msg.includes("syllabus") ||
      msg.includes("curriculum") ||
      msg.includes("programs") ||
      msg.includes("program") ||
      msg.includes("training")
    ) {
      return { action: "navigate", path: "/courses/" };
    }

    // ── Placements / Success Stories / Alumni ─────────────────
    // /success-stories does not exist — route to /placements/ instead
    if (
      msg.includes("placement") ||
      msg.includes("placements") ||
      msg.includes("success stories") ||
      msg.includes("success story") ||
      msg.includes("testimonials") ||
      msg.includes("reviews") ||
      msg.includes("alumni") ||
      msg.includes("job") ||
      msg.includes("salary") ||
      msg.includes("career")
    ) {
      return { action: "navigate", path: "/placements/" };
    }

    // ── Contact ───────────────────────────────────────────────
    if (
      msg.includes("contact") ||
      msg.includes("contact page") ||
      msg.includes("reach out") ||
      msg.includes("call me") ||
      msg.includes("email") ||
      msg.includes("whatsapp") ||
      msg.includes("fees") ||
      msg.includes("fee") ||
      msg.includes("price") ||
      msg.includes("pricing") ||
      msg.includes("cost") ||
      msg.includes("enroll") ||
      msg.includes("admission")
    ) {
      return { action: "navigate", path: "/contact/" };
    }

    // ── About ─────────────────────────────────────────────────
    if (
      msg.includes("about") ||
      msg.includes("about us") ||
      msg.includes("mission") ||
      msg.includes("vision") ||
      msg.includes("who are you") ||
      msg.includes("who is boffins") ||
      msg.includes("boffins academy")
    ) {
      return { action: "navigate", path: "/about/" };
    }

    // ── Gallery ───────────────────────────────────────────────
    if (
      msg.includes("gallery") ||
      msg.includes("photos") ||
      msg.includes("images") ||
      msg.includes("campus") ||
      msg.includes("life at")
    ) {
      return { action: "navigate", path: "/gallery/" };
    }

    // ── Instructors ───────────────────────────────────────────
    if (
      msg.includes("instructor") ||
      msg.includes("instructors") ||
      msg.includes("trainer") ||
      msg.includes("trainers") ||
      msg.includes("mentor") ||
      msg.includes("faculty") ||
      msg.includes("teachers")
    ) {
      return { action: "navigate", path: "/instructors/" };
    }

    return null;
  }

  return { detect };
})();