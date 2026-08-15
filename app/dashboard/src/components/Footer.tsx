import { BoxProps, HStack, Text } from "@chakra-ui/react";
import { FC } from "react";

export const Footer: FC<BoxProps> = (props) => {
  return (
    <HStack w="full" py="0" position="relative" {...props}>
      <Text
        flexGrow={1}
        textAlign="center"
        color="gray.500"
        fontSize="xs"
        letterSpacing="0.02em"
      >
        Heisenberg Panel · Private control laboratory
      </Text>
    </HStack>
  );
};
