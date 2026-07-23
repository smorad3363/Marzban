import { BoxProps, HStack, Text } from "@chakra-ui/react";
import { useDashboard } from "contexts/DashboardContext";
import { FC } from "react";

export const Footer: FC<BoxProps> = (props) => {
  const { version } = useDashboard();
  return (
    <HStack w="full" py="0" position="relative" {...props}>
      <Text
        flexGrow={1}
        textAlign="center"
        color="gray.500"
        fontSize="xs"
        letterSpacing="0.02em"
      >
        Private network control{version ? ` · Control plane v${version}` : ""}
      </Text>
    </HStack>
  );
};
