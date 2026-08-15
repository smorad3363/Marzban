import { extendTheme } from "@chakra-ui/react";
export const theme = extendTheme({
  shadows: {
    outline: "0 0 0 3px rgba(37, 99, 235, 0.2)",
    panel: "0 1px 2px rgba(15, 23, 42, 0.03), 0 12px 32px rgba(15, 23, 42, 0.055)",
    elevated: "0 18px 48px rgba(15, 23, 42, 0.12)",
  },
  fonts: {
    heading: `Manrope, Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`,
    body: `Manrope, Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`,
    mono: `IBM Plex Mono, SFMono-Regular, Consolas, monospace`,
  },
  colors: {
    "light-border": "#dfe5ef",
    surface: {
      light: "#ffffff",
      dark: "#0d1728",
    },
    primary: {
      50: "#eff6ff",
      100: "#dbeafe",
      200: "#bfdbfe",
      300: "#93c5fd",
      400: "#60a5fa",
      500: "#3b82f6",
      600: "#2563eb",
      700: "#1d4ed8",
      800: "#1e40af",
      900: "#1e3a8a",
    },
    gray: {
      750: "#172235",
    },
  },
  styles: {
    global: {
      body: {
        bg: "#f5f7fb",
        color: "#172033",
        _dark: {
          bg: "#07101d",
          color: "gray.100",
        },
      },
      "::selection": {
        bg: "primary.200",
        color: "gray.900",
      },
    },
  },
  components: {
    Button: {
      baseStyle: {
        borderRadius: "10px",
        fontWeight: "650",
        transitionProperty: "background-color, border-color, color",
        transitionDuration: "120ms",
      },
      sizes: {
        md: { h: "42px", px: 4 },
      },
    },
    Card: {
      baseStyle: {
        container: {
          bg: "white",
          borderColor: "light-border",
          _dark: { bg: "#0d1929", borderColor: "gray.600" },
        },
      },
    },
    Alert: {
      baseStyle: {
        container: {
          borderRadius: "10px",
          fontSize: "sm",
        },
      },
    },
    Select: {
      baseStyle: {
        field: {
          _dark: {
            borderColor: "gray.600",
            borderRadius: "6px",
          },
          _light: {
            borderRadius: "6px",
          },
        },
      },
    },
    FormHelperText: {
      baseStyle: {
        fontSize: "xs",
      },
    },
    FormLabel: {
      baseStyle: {
        fontSize: "sm",
        fontWeight: "medium",
        mb: "1",
        _dark: { color: "gray.300" },
      },
    },
    Input: {
      baseStyle: {
        addon: {
          _dark: {
            borderColor: "gray.600",
            _placeholder: {
              color: "gray.500",
            },
          },
        },
        field: {
          borderRadius: "10px",
          bg: "white",
          _focusVisible: {
            boxShadow: "none",
            borderColor: "primary.200",
            outlineColor: "primary.200",
          },
          _dark: {
            bg: "whiteAlpha.50",
            borderColor: "gray.600",
            _disabled: {
              color: "gray.400",
              borderColor: "gray.500",
            },
            _placeholder: {
              color: "gray.500",
            },
          },
        },
      },
    },
    Table: {
      baseStyle: {
        table: {
          borderCollapse: "separate",
          borderSpacing: 0,
        },
        thead: {
          borderBottomColor: "light-border",
        },
        th: {
          background: "#f8fafc",
          color: "gray.500",
          fontSize: "xs",
          letterSpacing: "0.04em",
          borderColor: "light-border !important",
          borderBottomColor: "light-border !important",
          borderTop: "1px solid ",
          borderTopColor: "light-border !important",
          _first: {
            borderLeft: "1px solid",
            borderColor: "light-border !important",
          },
          _last: {
            borderRight: "1px solid",
            borderColor: "light-border !important",
          },
          _dark: {
            borderColor: "gray.600 !important",
            background: "gray.750",
          },
        },
        td: {
          transition: "background-color .12s ease-out",
          py: 4,
          borderColor: "light-border",
          borderBottomColor: "light-border !important",
          _first: {
            borderLeft: "1px solid",
            borderColor: "light-border",
            _dark: {
              borderColor: "gray.600",
            },
          },
          _last: {
            borderRight: "1px solid",
            borderColor: "light-border",
            _dark: {
              borderColor: "gray.600",
            },
          },
          _dark: {
            borderColor: "gray.600",
            borderBottomColor: "gray.600 !important",
          },
        },
        tr: {
          "&.interactive": {
            cursor: "pointer",
            _hover: {
              "& > td": {
                  bg: "primary.50",
              },
              _dark: {
                "& > td": {
                  bg: "gray.750",
                },
              },
            },
          },
          _last: {
            "& > td": {
              _first: {
                borderBottomLeftRadius: "8px",
              },
              _last: {
                borderBottomRightRadius: "8px",
              },
            },
          },
        },
      },
    },
  },
});
