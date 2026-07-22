import {
  BoxProps,
  Button,
  chakra,
  Grid,
  GridItem,
  HStack,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  InputRightElement,
  Select,
  Spinner,
  Text,
} from "@chakra-ui/react";
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import classNames from "classnames";
import { useDashboard } from "contexts/DashboardContext";
import debounce from "lodash.debounce";
import React, { FC, useState } from "react";
import { useTranslation } from "react-i18next";

const iconProps = {
  baseStyle: {
    w: 4,
    h: 4,
  },
};

const SearchIcon = chakra(MagnifyingGlassIcon, iconProps);
const ClearIcon = chakra(XMarkIcon, iconProps);
export const ReloadIcon = chakra(ArrowPathIcon, iconProps);

export type FilterProps = {} & BoxProps;
const setSearchField = debounce((search: string) => {
  useDashboard.getState().onFilterChange({
    ...useDashboard.getState().filters,
    offset: 0,
    search,
  });
}, 300);

export const Filters: FC<FilterProps> = ({ ...props }) => {
  const { loading, filters, onFilterChange, refetchUsers, onCreateUser } =
    useDashboard();
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setSearchField(e.target.value);
  };
  const clear = () => {
    setSearch("");
    onFilterChange({
      ...filters,
      offset: 0,
      search: "",
    });
  };
  const changeSort = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({ sort: e.target.value, offset: 0 });
  };
  const changeStatus = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({
      status: e.target.value
        ? (e.target.value as typeof filters.status)
        : undefined,
      offset: 0,
    });
  };
  return (
    <Grid
      id="filters"
      templateColumns={{
        lg: "repeat(3, 1fr)",
        md: "repeat(4, 1fr)",
        base: "repeat(1, 1fr)",
      }}
      position="sticky"
      top={0}
      mx="-6"
      px="6"
      rowGap={4}
      gap={{
        lg: 4,
        base: 0,
      }}
      bg="var(--chakra-colors-chakra-body-bg)"
      py={4}
      zIndex="docked"
      {...props}
    >
      <GridItem colSpan={{ base: 1, md: 2, lg: 1 }} order={{ base: 2, md: 1 }}>
        <InputGroup>
          <InputLeftElement pointerEvents="none" children={<SearchIcon />} />
          <Input
            placeholder={t("search")}
            value={search}
            borderColor="light-border"
            onChange={onChange}
          />

          <InputRightElement>
            {loading && <Spinner size="xs" />}
            {filters.search && filters.search.length > 0 && (
              <IconButton
                onClick={clear}
                aria-label="clear"
                size="xs"
                variant="ghost"
              >
                <ClearIcon />
              </IconButton>
            )}
          </InputRightElement>
        </InputGroup>
      </GridItem>
      <GridItem colSpan={2} order={{ base: 1, md: 2 }}>
        <HStack justifyContent="flex-end" alignItems="center" h="full">
          <IconButton
            aria-label="refresh users"
            disabled={loading}
            onClick={refetchUsers}
            size="sm"
            variant="outline"
          >
            <ReloadIcon
              className={classNames({
                "animate-spin": loading,
              })}
            />
          </IconButton>
          <Button
            colorScheme="primary"
            size="sm"
            onClick={() => onCreateUser(true)}
            px={5}
          >
            {t("createUser")}
          </Button>
        </HStack>
      </GridItem>
      <GridItem
        colSpan={{ base: 1, md: 4, lg: 3 }}
        order={3}
        borderTop="1px solid"
        borderColor="light-border"
        pt={3}
      >
        <HStack
          spacing={3}
          justify="flex-end"
          flexWrap="wrap"
          fontSize="sm"
        >
          <Text color="gray.500" fontWeight="medium" whiteSpace="nowrap">
            {t("usersTable.organizeUsers")}
          </Text>
          <Select
            aria-label={t("usersTable.filterStatus")}
            value={filters.status || ""}
            onChange={changeStatus}
            size="sm"
            rounded="md"
            w={{ base: "full", sm: "170px" }}
            bg="chakra-body-bg"
          >
            <option value="">{t("usersTable.allStatuses")}</option>
            <option value="active">{t("active")}</option>
            <option value="on_hold">{t("on_hold")}</option>
            <option value="disabled">{t("disabled")}</option>
            <option value="limited">{t("limited")}</option>
            <option value="expired">{t("expired")}</option>
          </Select>
          <Select
            aria-label={t("usersTable.sortBy")}
            value={filters.sort}
            onChange={changeSort}
            size="sm"
            rounded="md"
            w={{ base: "full", sm: "220px" }}
            bg="chakra-body-bg"
          >
            <option value="-created_at">{t("usersTable.newestFirst")}</option>
            <option value="created_at">{t("usersTable.oldestFirst")}</option>
            <option value="username">{t("usersTable.usernameAZ")}</option>
            <option value="-username">{t("usersTable.usernameZA")}</option>
            <option value="-used_traffic">{t("usersTable.usageHighLow")}</option>
            <option value="used_traffic">{t("usersTable.usageLowHigh")}</option>
            <option value="expire">{t("usersTable.expireSoon")}</option>
            <option value="-expire">{t("usersTable.expireLate")}</option>
          </Select>
        </HStack>
      </GridItem>
    </Grid>
  );
};
