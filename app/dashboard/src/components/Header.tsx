import {
  Box,
  Button,
  chakra,
  Flex,
  HStack,
  IconButton,
  Image,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Spacer,
  Stack,
  Text,
  useColorMode,
} from "@chakra-ui/react";
import {
  ArrowLeftOnRectangleIcon,
  Bars3Icon,
  ChartPieIcon,
  Cog6ToothIcon,
  DocumentMinusIcon,
  LinkIcon,
  MoonIcon,
  SquaresPlusIcon,
  SunIcon,
  UserGroupIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import brandIcon from "assets/brand/secure-network-icon.png";
import { useDashboard } from "contexts/DashboardContext";
import { FC, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";
import { updateThemeColor } from "utils/themeColor";
import { Language } from "./Language";
import useGetUser from "hooks/useGetUser";

type HeaderProps = {
  actions?: ReactNode;
};
const iconProps = {
  baseStyle: {
    w: 4,
    h: 4,
  },
};

const DarkIcon = chakra(MoonIcon, iconProps);
const LightIcon = chakra(SunIcon, iconProps);
const CoreSettingsIcon = chakra(Cog6ToothIcon, iconProps);
const SettingsIcon = chakra(Bars3Icon, iconProps);
const LogoutIcon = chakra(ArrowLeftOnRectangleIcon, iconProps);
const HostsIcon = chakra(LinkIcon, iconProps);
const NodesIcon = chakra(SquaresPlusIcon, iconProps);
const NodesUsageIcon = chakra(ChartPieIcon, iconProps);
const ResetUsageIcon = chakra(DocumentMinusIcon, iconProps);
const UsersNavIcon = chakra(UsersIcon, iconProps);
const AdminsNavIcon = chakra(UserGroupIcon, iconProps);
export const Header: FC<HeaderProps> = ({ actions }) => {
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();

  const isSudo = () => {
    if (!getUserIsPending && getUserIsSuccess) {
      return userData.is_sudo;
    }
    return false;
  };

  const {
    onEditingHosts,
    onResetAllUsage,
    onEditingNodes,
    onShowingNodesUsage,
  } = useDashboard();
  const { t } = useTranslation();
  const location = useLocation();
  const isAdminsPage = location.pathname.startsWith("/admins");
  const { colorMode, toggleColorMode } = useColorMode();
  return (
    <Flex
      as="aside"
      w={{ base: "full", lg: "252px" }}
      minW={{ lg: "252px" }}
      minH={{ lg: "100vh" }}
      h={{ lg: "100vh" }}
      position={{ base: "relative", lg: "sticky" }}
      top="0"
      zIndex="sticky"
      direction="column"
      bg="whiteAlpha.900"
      _dark={{ bg: "rgba(8, 17, 31, 0.94)", borderColor: "whiteAlpha.200" }}
      borderEndWidth={{ lg: "1px" }}
      borderBottomWidth={{ base: "1px", lg: "0" }}
      borderColor="gray.200"
      backdropFilter="blur(18px)"
      px={{ base: 4, lg: 4 }}
      py={{ base: 3, lg: 5 }}
      __css={{
        "& .menuList": {
          direction: "ltr",
        },
      }}
    >
      <HStack justify="space-between" align="center">
        <HStack spacing={3} minW={0}>
          <Image
            src={brandIcon}
            alt="Network console"
            boxSize={{ base: "38px", lg: "46px" }}
            borderRadius="14px"
            objectFit="cover"
            boxShadow="0 10px 30px rgba(37, 99, 235, 0.2)"
          />
          <Box minW={0}>
            <Text fontSize="xs" fontWeight="800" letterSpacing="0.13em" color="primary.600" _dark={{ color: "primary.300" }}>
              MARZBAN
            </Text>
            <Text fontSize="xs" color="gray.500" mt="1px">
              Control center
            </Text>
          </Box>
        </HStack>
        <HStack display={{ base: "flex", lg: "none" }} spacing={2}>
          <Menu>
            <MenuButton as={IconButton} size="sm" variant="ghost" icon={<SettingsIcon />} aria-label="settings" />
            <MenuList minW="190px" zIndex={99999} className="menuList">
              {isSudo() && (
                <>
                  <MenuItem icon={<CoreSettingsIcon />} onClick={() => useDashboard.setState({ isEditingCore: true })}>
                    {t("core.title")}
                  </MenuItem>
                  <MenuItem icon={<HostsIcon />} onClick={onEditingHosts.bind(null, true)}>
                    {t("header.hostSettings")}
                  </MenuItem>
                  <MenuItem icon={<NodesIcon />} onClick={onEditingNodes.bind(null, true)}>
                    {t("header.nodeSettings")}
                  </MenuItem>
                  <MenuItem icon={<NodesUsageIcon />} onClick={onShowingNodesUsage.bind(null, true)}>
                    {t("header.nodesUsage")}
                  </MenuItem>
                  <MenuItem icon={<ResetUsageIcon />} onClick={onResetAllUsage.bind(null, true)}>
                    {t("resetAllUsage")}
                  </MenuItem>
                </>
              )}
              <Link to="/login">
                <MenuItem icon={<LogoutIcon />}>{t("header.logout")}</MenuItem>
              </Link>
            </MenuList>
          </Menu>
          <Language />
          <IconButton
            size="sm"
            variant="ghost"
            aria-label="switch theme"
            onClick={() => {
              updateThemeColor(colorMode == "dark" ? "light" : "dark");
              toggleColorMode();
            }}
          >
            {colorMode === "light" ? <DarkIcon /> : <LightIcon />}
          </IconButton>
        </HStack>
      </HStack>

      <Stack
        as="nav"
        direction={{ base: "row", lg: "column" }}
        spacing={{ base: 2, lg: 1 }}
        mt={{ base: 3, lg: 9 }}
        overflowX={{ base: "auto", lg: "visible" }}
      >
          <Button as={Link} to="/" size="md" variant={!isAdminsPage ? "solid" : "ghost"} colorScheme={!isAdminsPage ? "primary" : "gray"} leftIcon={<UsersNavIcon />} justifyContent="flex-start" minW={{ base: "max-content", lg: "full" }}>
            {t("users")}
          </Button>
          {isSudo() && (
            <Button as={Link} to="/admins/" size="md" variant={isAdminsPage ? "solid" : "ghost"} colorScheme={isAdminsPage ? "primary" : "gray"} leftIcon={<AdminsNavIcon />} justifyContent="flex-start" minW={{ base: "max-content", lg: "full" }}>
              {t("admins.nav")}
            </Button>
          )}
      </Stack>

      <Spacer display={{ base: "none", lg: "block" }} />
      {actions}
      <Box display={{ base: "none", lg: "block" }} mt={6} pt={4} borderTopWidth="1px" borderColor="gray.200" _dark={{ borderColor: "whiteAlpha.200" }}>
        <Text fontSize="xs" color="gray.500" mb={3} px={1} noOfLines={1}>
          {userData?.username || "Administrator"}
        </Text>
        <HStack alignItems="center" spacing={2}>
          <Menu>
            <MenuButton
              as={IconButton}
              size="sm"
              variant="outline"
              icon={
                <>
                  <SettingsIcon />
                </>
              }
              position="relative"
            ></MenuButton>
            <MenuList minW="170px" zIndex={99999} className="menuList">
              {isSudo() && (
                <>
                  <MenuItem
                    maxW="170px"
                    fontSize="sm"
                    icon={<HostsIcon />}
                    onClick={onEditingHosts.bind(null, true)}
                  >
                    {t("header.hostSettings")}
                  </MenuItem>
                  <MenuItem
                    maxW="170px"
                    fontSize="sm"
                    icon={<NodesIcon />}
                    onClick={onEditingNodes.bind(null, true)}
                  >
                    {t("header.nodeSettings")}
                  </MenuItem>
                  <MenuItem
                    maxW="170px"
                    fontSize="sm"
                    icon={<NodesUsageIcon />}
                    onClick={onShowingNodesUsage.bind(null, true)}
                  >
                    {t("header.nodesUsage")}
                  </MenuItem>
                  <MenuItem
                    maxW="170px"
                    fontSize="sm"
                    icon={<ResetUsageIcon />}
                    onClick={onResetAllUsage.bind(null, true)}
                  >
                    {t("resetAllUsage")}
                  </MenuItem>
                </>
              )}
              <Link to="/login">
                <MenuItem maxW="170px" fontSize="sm" icon={<LogoutIcon />}>
                  {t("header.logout")}
                </MenuItem>
              </Link>
            </MenuList>
          </Menu>

          {isSudo() && (
            <IconButton
              size="sm"
              variant="outline"
              aria-label="core settings"
              onClick={() => {
                useDashboard.setState({ isEditingCore: true });
              }}
            >
              <CoreSettingsIcon />
            </IconButton>
          )}

          <Language />

          <IconButton
            size="sm"
            variant="outline"
            aria-label="switch theme"
            onClick={() => {
              updateThemeColor(colorMode == "dark" ? "light" : "dark");
              toggleColorMode();
            }}
          >
            {colorMode === "light" ? <DarkIcon /> : <LightIcon />}
          </IconButton>
        </HStack>
      </Box>
    </Flex>
  );
};
