import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useVenueFilter, STORAGE_KEY } from "./useVenueFilter";
import type { Venue } from "./types";

function venue(id: string, kind: Venue["kind"] = "independent"): Venue {
  return { id, name: id, arrondissement: 5, kind, chain: null,
           coverage: "allocine", accessibility: null };
}

const VENUES = [venue("a"), venue("b"), venue("c"), venue("ugc-1", "chain")];

beforeEach(() => localStorage.clear());

describe("useVenueFilter", () => {
  it("shows everything by default", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.isFiltered).toBe(false);
    expect(result.current.visibleCount).toBe(3);
    expect(result.current.totalCount).toBe(3);
  });

  it("counts only independents", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.totalCount).toBe(3); // ugc-1 excluded
  });

  it("toggling hides then shows again", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.toggle("a"));
    expect(result.current.isVisible("a")).toBe(false);
    expect(result.current.visibleCount).toBe(2);
    expect(result.current.isFiltered).toBe(true);
    act(() => result.current.toggle("a"));
    expect(result.current.isVisible("a")).toBe(true);
    expect(result.current.isFiltered).toBe(false);
  });

  it("persists hidden ids to localStorage", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.toggle("b"));
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!)).toEqual(["b"]);
  });

  it("restores hidden ids from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["c"]));
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.isVisible("c")).toBe(false);
    expect(result.current.visibleCount).toBe(2);
  });

  it("a venue added after the filter was set stays visible", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["a"]));
    const { result } = renderHook(() =>
      useVenueFilter([...VENUES, venue("brand-new")])
    );
    expect(result.current.isVisible("brand-new")).toBe(true);
  });

  it("showAll clears everything", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["a", "b"]));
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.showAll());
    expect(result.current.isFiltered).toBe(false);
    expect(result.current.visibleCount).toBe(3);
  });

  it("hideAll hides the ids given", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.hideAll(["a", "b", "c"]));
    expect(result.current.visibleCount).toBe(0);
  });

  it("survives corrupt localStorage", () => {
    localStorage.setItem(STORAGE_KEY, "not json");
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.isFiltered).toBe(false);
    expect(result.current.visibleCount).toBe(3);
  });

  it("setVisible hides multiple ids at once", () => {
    const { result } = renderHook(() => useVenueFilter(VENUES));
    act(() => result.current.setVisible(["a", "b"], false));
    expect(result.current.isVisible("a")).toBe(false);
    expect(result.current.isVisible("b")).toBe(false);
    expect(result.current.visibleCount).toBe(1);
  });

  it("setVisible un-hides previously hidden ids", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["a", "b"]));
    const { result } = renderHook(() => useVenueFilter(VENUES));
    expect(result.current.visibleCount).toBe(1);
    act(() => result.current.setVisible(["a", "b"], true));
    expect(result.current.isVisible("a")).toBe(true);
    expect(result.current.isVisible("b")).toBe(true);
    expect(result.current.visibleCount).toBe(3);
    expect(result.current.isFiltered).toBe(false);
  });
});
