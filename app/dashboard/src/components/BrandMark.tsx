import { Box, BoxProps } from "@chakra-ui/react";
import { FC } from "react";

export const BrandMark: FC<BoxProps> = (props) => (
  <Box
    as="svg"
    viewBox="0 0 56 56"
    role="img"
    aria-label="Heisenberg Panel"
    flexShrink={0}
    {...props}
  >
    <defs>
      <linearGradient id="heisenberg-mark" x1="7" y1="4" x2="49" y2="52">
        <stop stopColor="#48D58B" />
        <stop offset="1" stopColor="#167548" />
      </linearGradient>
    </defs>
    <rect x="2" y="2" width="52" height="52" rx="8" fill="#07130E" />
    <rect x="5" y="5" width="46" height="46" rx="6" fill="url(#heisenberg-mark)" />
    <path d="M9 16h38M16 9v38" stroke="#E8FFF2" strokeOpacity=".18" />
    <text x="10" y="14" fill="#E8FFF2" fontFamily="monospace" fontSize="7" fontWeight="700">2</text>
    <text x="28" y="37" fill="#FFFFFF" fontFamily="monospace" fontSize="25" fontWeight="700" textAnchor="middle">He</text>
    <text x="28" y="46" fill="#D8FFE8" fontFamily="monospace" fontSize="5" fontWeight="600" letterSpacing="1" textAnchor="middle">CONTROL</text>
  </Box>
);
