import { ColorMode } from "@chakra-ui/react";

export const updateThemeColor = (colorMode: ColorMode) => {
  const el = document.querySelector('meta[name="theme-color"]');
  el?.setAttribute("content", colorMode == "dark" ? "#07111f" : "#f4f8fb");
};
