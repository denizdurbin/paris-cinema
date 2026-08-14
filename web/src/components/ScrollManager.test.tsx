import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { ScrollManager } from "./ScrollManager";

function setScrollY(y: number) {
  Object.defineProperty(window, "scrollY", { value: y, configurable: true });
}

function BackButton() {
  const navigate = useNavigate();
  return <button onClick={() => navigate(-1)}>back</button>;
}

function TestApp() {
  return (
    <>
      <ScrollManager />
      <Routes>
        <Route path="/" element={<Link to="/film">film</Link>} />
        <Route path="/film" element={<BackButton />} />
      </Routes>
    </>
  );
}

describe("ScrollManager", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setScrollY(0);
  });

  it("scrolls to top on push and restores the saved position on back", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    render(<MemoryRouter><TestApp /></MemoryRouter>);

    // The user has scrolled down the list, then opens a film.
    setScrollY(500);
    fireEvent.scroll(window); // the manager records positions on scroll
    fireEvent.click(screen.getByText("film"));
    expect(scrollTo).toHaveBeenLastCalledWith(0, 0);

    // The browser is now at the top of the film page; going back must
    // restore where the list was left.
    setScrollY(0);
    fireEvent.click(screen.getByText("back"));
    expect(scrollTo).toHaveBeenLastCalledWith(0, 500);
  });
});
