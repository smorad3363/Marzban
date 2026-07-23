import {
  Alert,
  AlertDescription,
  AlertIcon,
  Box,
  Button,
  Flex,
  FormControl,
  Grid,
  HStack,
  Image,
  Text,
  VStack,
} from "@chakra-ui/react";
import { ArrowRightOnRectangleIcon } from "@heroicons/react/24/outline";
import { zodResolver } from "@hookform/resolvers/zod";
import brandIcon from "assets/brand/secure-network-icon.png";
import networkHero from "assets/brand/secure-network-hero.png";
import { Footer } from "components/Footer";
import { Input } from "components/Input";
import { Language } from "components/Language";
import { FC, useEffect, useState } from "react";
import { FieldValues, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { fetch } from "service/http";
import { removeAuthToken, setAuthToken } from "utils/authStorage";
import { z } from "zod";

const schema = z.object({
  username: z.string().min(1, "login.fieldRequired"),
  password: z.string().min(1, "login.fieldRequired"),
});

export const Login: FC = () => {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();
  const location = useLocation();
  const {
    register,
    formState: { errors },
    handleSubmit,
  } = useForm({ resolver: zodResolver(schema) });

  useEffect(() => {
    removeAuthToken();
    if (location.pathname !== "/login") navigate("/login", { replace: true });
  }, []);

  const login = (values: FieldValues) => {
    setError("");
    const formData = new FormData();
    formData.append("username", values.username);
    formData.append("password", values.password);
    formData.append("grant_type", "password");
    setLoading(true);
    fetch("/admin/token", { method: "post", body: formData })
      .then(({ access_token: token }) => {
        setAuthToken(token);
        navigate("/");
      })
      .catch((err) => setError(err.response._data.detail))
      .finally(setLoading.bind(null, false));
  };

  return (
    <Grid
      minH="100vh"
      templateColumns={{ base: "1fr", lg: "minmax(420px, 0.78fr) 1.22fr" }}
      bg="white"
      _dark={{ bg: "#08111f" }}
    >
      <Flex
        direction="column"
        minH="100vh"
        px={{ base: 6, md: 12 }}
        py={{ base: 6, md: 8 }}
        borderRight={{ lg: "1px solid" }}
        borderColor={{ lg: "gray.200" }}
        _dark={{ borderColor: "whiteAlpha.200" }}
      >
        <HStack justifyContent="space-between" w="full">
          <HStack spacing={3}>
            <Image
              src={brandIcon}
              alt="Secure network gateway"
              boxSize="42px"
              borderRadius="13px"
              objectFit="cover"
              boxShadow="0 10px 30px rgba(8, 145, 178, 0.22)"
            />
            <Box>
              <Text
                fontSize="xs"
                fontWeight="800"
                letterSpacing="0.16em"
                color="primary.600"
                _dark={{ color: "primary.300" }}
              >
                NETWORK CONSOLE
              </Text>
              <Text fontSize="xs" color="gray.500">
                Secure control plane
              </Text>
            </Box>
          </HStack>
          <Language />
        </HStack>

        <Flex flex="1" align="center" justify="center" py={12}>
          <Box w="full" maxW="390px">
            <VStack alignItems="flex-start" w="full" spacing={2}>
              <Text
                fontSize={{ base: "3xl", md: "4xl" }}
                lineHeight="1.08"
                letterSpacing="-0.035em"
                fontWeight="750"
              >
                {t("login.loginYourAccount")}
              </Text>
              <Text color="gray.600" _dark={{ color: "gray.400" }} maxW="34ch">
                {t("login.welcomeBack")}
              </Text>
            </VStack>

            <Box w="full" pt="7">
              <form onSubmit={handleSubmit(login)}>
                <VStack rowGap={3}>
                  <FormControl>
                    <Input
                      w="full"
                      label={t("username")}
                      placeholder={t("username")}
                      {...register("username")}
                      error={t(errors?.username?.message as string)}
                    />
                  </FormControl>
                  <FormControl>
                    <Input
                      w="full"
                      label={t("password")}
                      type="password"
                      placeholder={t("password")}
                      {...register("password")}
                      error={t(errors?.password?.message as string)}
                    />
                  </FormControl>
                  {error && (
                    <Alert status="error" rounded="md">
                      <AlertIcon />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}
                  <Button
                    isLoading={loading}
                    type="submit"
                    w="full"
                    colorScheme="primary"
                    mt={2}
                    h="44px"
                    rightIcon={<ArrowRightOnRectangleIcon width="18px" />}
                  >
                    {t("login")}
                  </Button>
                </VStack>
              </form>
            </Box>
          </Box>
        </Flex>
        <Footer />
      </Flex>

      <Box
        display={{ base: "none", lg: "block" }}
        position="relative"
        overflow="hidden"
        bg="#07111f"
      >
        <Image
          src={networkHero}
          alt="Encrypted network routing"
          position="absolute"
          inset={0}
          w="full"
          h="full"
          objectFit="cover"
        />
        <Box
          position="absolute"
          inset={0}
          bgGradient="linear(to-t, rgba(4, 11, 24, 0.92) 0%, transparent 52%, rgba(4, 11, 24, 0.2) 100%)"
        />
        <Box position="absolute" left={12} right={12} bottom={12} color="white">
          <Text
            fontSize="xs"
            fontWeight="800"
            letterSpacing="0.18em"
            color="cyan.200"
            mb={3}
          >
            ENCRYPTED OPERATIONS
          </Text>
          <Text fontSize="3xl" fontWeight="650" letterSpacing="-0.025em">
            Every route visible. Every edge controlled.
          </Text>
        </Box>
      </Box>
    </Grid>
  );
};

export default Login;
