import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import {
  Link, MemoryRouter, Route, Routes, useLocation, useNavigationType,
} from "react-router-dom";
import { BackLink } from "./BackLink";

function Path() {
  const location = useLocation();
  const navType = useNavigationType();
  return <span data-testid="path">{`${location.pathname}:${navType}`}</span>;
}

function TestApp() {
  return (
    <>
      <Path />
      <Routes>
        <Route path="/" element={<Link to="/film">film</Link>} />
        <Route path="/film" element={<BackLink to="/">back</BackLink>} />
      </Routes>
    </>
  );
}

// vitest runs without globals here, so @testing-library's auto-cleanup is
// off; without it both renders stay in the document and queries ambiguous.
afterEach(cleanup);

describe("BackLink", () => {
  it("pops history when the user arrived from inside the app", () => {
    render(<MemoryRouter><TestApp /></MemoryRouter>);
    fireEvent.click(screen.getByText("film"));
    expect(screen.getByTestId("path").textContent).toBe("/film:PUSH");
    fireEvent.click(screen.getByText("back"));
    expect(screen.getByTestId("path").textContent).toBe("/:POP");
  });

  it("follows the link on a direct visit with no in-app history", () => {
    render(<MemoryRouter initialEntries={["/film"]}><TestApp /></MemoryRouter>);
    fireEvent.click(screen.getByText("back"));
    expect(screen.getByTestId("path").textContent).toBe("/:PUSH");
  });
});
