import { extendTheme } from "@chakra-ui/react";
export const theme = extendTheme({
  config: {
    initialColorMode: "dark",
    useSystemColorMode: false,
  },
  shadows: {
    outline: "0 0 0 3px rgba(34, 197, 94, 0.24)",
    panel: "0 1px 2px rgba(0, 0, 0, 0.32), 0 14px 34px rgba(0, 0, 0, 0.24)",
    elevated: "0 22px 54px rgba(0, 0, 0, 0.42)",
  },
  fonts: {
    heading: `Fira Sans, Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`,
    body: `Fira Sans, Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`,
    mono: `Fira Code, IBM Plex Mono, Consolas, monospace`,
  },
  colors: {
    "light-border": "#33483b",
    surface: {
      light: "#111d17",
      dark: "#111d17",
    },
    primary: {
      50: "#eafbf1",
      100: "#c9f4da",
      200: "#9ce9ba",
      300: "#67d994",
      400: "#3fc978",
      500: "#22b965",
      600: "#168e4c",
      700: "#126f3e",
      800: "#115833",
      900: "#0d482b",
    },
    gold: {
      50: "#fff9e8",
      100: "#f8e9b6",
      200: "#ecd483",
      300: "#ddbd55",
      400: "#caa53d",
      500: "#ad8529",
      600: "#896720",
      700: "#684e1c",
      800: "#493817",
      900: "#2d2413",
    },
    gray: {
      750: "#172235",
    },
  },
  styles: {
    global: {
      body: {
        bg: "#09130e",
        color: "gray.100",
        lineHeight: "1.5",
        _dark: {
          bg: "#09130e",
          color: "gray.100",
        },
      },
      'html[lang^="fa"]': {
        "--chakra-fonts-heading": `Vazirmatn, Fira Sans, sans-serif`,
        "--chakra-fonts-body": `Vazirmatn, Fira Sans, sans-serif`,
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
        borderRadius: "8px",
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
          bg: "#111d17",
          color: "gray.100",
          borderColor: "#33483b",
          _dark: { bg: "#111d17", borderColor: "#33483b" },
        },
      },
    },
    Modal: {
      baseStyle: {
        dialog: {
          bg: "#111d17",
          color: "gray.100",
          borderWidth: "1px",
          borderColor: "#33483b",
          _dark: { bg: "#111d17", borderColor: "#33483b" },
        },
        header: { borderColor: "#33483b", _dark: { borderColor: "#33483b" } },
        footer: { borderColor: "#33483b", _dark: { borderColor: "#33483b" } },
      },
    },
    Alert: {
      baseStyle: {
        container: {
          borderRadius: "8px",
          fontSize: "sm",
        },
      },
    },
    Select: {
      baseStyle: {
        field: {
          bg: "#111d17",
          color: "gray.100",
          borderColor: "#475f50",
          borderRadius: "6px",
          _dark: {
            bg: "#111d17",
            color: "gray.100",
            borderColor: "#475f50",
            borderRadius: "6px",
          },
        },
      },
      sizes: {
        sm: { field: { minH: "44px", fontSize: "sm", px: 3 } },
        md: { field: { minH: "44px", fontSize: "sm", px: 3 } },
      },
    },
    FormHelperText: {
      baseStyle: {
        fontSize: "xs",
        color: "gray.400",
      },
    },
    FormLabel: {
      baseStyle: {
        fontSize: "sm",
        fontWeight: "medium",
        mb: "1",
        lineHeight: "1.7",
        whiteSpace: "normal",
        overflowWrap: "anywhere",
        color: "gray.300",
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
          bg: "whiteAlpha.50",
          color: "gray.100",
          borderColor: "gray.600",
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
      sizes: {
        sm: {
          field: { minH: "44px", fontSize: "sm", px: 3 },
          addon: { minH: "44px", fontSize: "sm", px: 3 },
        },
        md: {
          field: { minH: "44px", fontSize: "sm", px: 3 },
          addon: { minH: "44px", fontSize: "sm", px: 3 },
        },
      },
    },
    Textarea: {
      baseStyle: {
        bg: "whiteAlpha.50",
        color: "gray.100",
        borderColor: "gray.600",
        lineHeight: "1.8",
        _placeholder: { color: "gray.500" },
        _focusVisible: { borderColor: "primary.300", boxShadow: "outline" },
      },
    },
    Table: {
      baseStyle: {
        table: {
          borderCollapse: "separate",
          borderSpacing: 0,
        },
        thead: {
          borderBottomColor: "#33483b",
        },
        th: {
          background: "#16251c",
          color: "gray.300",
          fontSize: "xs",
          letterSpacing: "0.04em",
          borderColor: "#33483b !important",
          borderBottomColor: "#33483b !important",
          borderTop: "1px solid ",
          borderTopColor: "#33483b !important",
          _first: {
            borderInlineStart: "1px solid",
            borderColor: "#33483b !important",
          },
          _last: {
            borderInlineEnd: "1px solid",
            borderColor: "#33483b !important",
          },
          _dark: {
            borderColor: "gray.600 !important",
            background: "#16251c",
          },
        },
        td: {
          transition: "background-color .12s ease-out",
          py: 4,
          color: "gray.100",
          borderColor: "#33483b",
          borderBottomColor: "#33483b !important",
          _first: {
            borderInlineStart: "1px solid",
            borderColor: "#33483b",
            _dark: {
              borderColor: "gray.600",
            },
          },
          _last: {
            borderInlineEnd: "1px solid",
            borderColor: "#33483b",
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
                  bg: "#16251c",
              },
              _dark: {
                "& > td": {
                  bg: "#16251c",
                },
              },
            },
          },
          _last: {
            "& > td": {
              _first: {
                borderEndStartRadius: "8px",
              },
              _last: {
                borderEndEndRadius: "8px",
              },
            },
          },
        },
      },
    },
  },
});
