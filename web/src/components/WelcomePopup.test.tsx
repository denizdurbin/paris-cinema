import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { WelcomePopup, WELCOME_KEY } from "./WelcomePopup";

beforeEach(() => localStorage.clear());
afterEach(() => cleanup());

describe("WelcomePopup", () => {
  it("shows on first visit", () => {
    render(<WelcomePopup />);
    expect(screen.getByText(/To the love of my life/)).toBeTruthy();
  });

  it("stays hidden once welcomed", () => {
    localStorage.setItem(WELCOME_KEY, "1");
    render(<WelcomePopup />);
    expect(screen.queryByText(/To the love of my life/)).toBeNull();
  });

  it("dismisses on close and persists the flag", () => {
    render(<WelcomePopup />);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(screen.queryByText(/To the love of my life/)).toBeNull();
    expect(localStorage.getItem(WELCOME_KEY)).toBe("1");
  });

  it("dismisses on Escape", () => {
    render(<WelcomePopup />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText(/To the love of my life/)).toBeNull();
  });
});
