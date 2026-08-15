import {
  chakra,
  HStack,
  IconButton,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
  useColorModeValue,
} from "@chakra-ui/react";
import { CheckIcon, LanguageIcon } from "@heroicons/react/24/outline";
import { FC } from "react";
import { useTranslation } from "react-i18next";

const LangIcon = chakra(LanguageIcon, { baseStyle: { w: 4, h: 4 } });
const SelectedIcon = chakra(CheckIcon, { baseStyle: { w: 4, h: 4 } });

const languages = [
  { code: "en", label: "English", dir: "ltr" },
  { code: "fa", label: "فارسی", dir: "rtl" },
  { code: "zh-cn", label: "简体中文", dir: "ltr" },
  { code: "ru", label: "Русский", dir: "ltr" },
] as const;

export const Language: FC = () => {
  const { i18n } = useTranslation();
  const current = (i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const menuBg = useColorModeValue("white", "#132019");
  const menuColor = useColorModeValue("#17231c", "#f1f5f2");
  const hoverBg = useColorModeValue("primary.50", "rgba(72, 213, 139, .12)");
  const menuBorder = useColorModeValue("gray.200", "#33483b");

  return (
    <Menu placement="bottom-end" closeOnSelect>
      <MenuButton
        as={IconButton}
        size="sm"
        variant="outline"
        color="inherit"
        borderColor="currentColor"
        opacity={0.9}
        _hover={{ opacity: 1, bg: "whiteAlpha.100" }}
        icon={<LangIcon />}
        aria-label="Change language"
      />
      <MenuList minW="168px" zIndex={9999} bg={menuBg} color={menuColor} borderColor={menuBorder} boxShadow="elevated" py={1.5}>
        {languages.map((language) => {
          const selected = current === language.code || (language.code === "en" && current.startsWith("en"));
          return (
            <MenuItem
              key={language.code}
              bg={selected ? hoverBg : "transparent"}
              color={menuColor}
              _hover={{ bg: hoverBg }}
              _focus={{ bg: hoverBg }}
              onClick={() => i18n.changeLanguage(language.code)}
              fontSize="sm"
              minH="40px"
            >
              <HStack w="full" justify="space-between" dir={language.dir}>
                <Text>{language.label}</Text>
                {selected && <SelectedIcon aria-hidden="true" color="primary.500" />}
              </HStack>
            </MenuItem>
          );
        })}
      </MenuList>
    </Menu>
  );
};
