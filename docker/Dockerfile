ARG UBUNTU_VERSION=24.04
ARG NVIDIA_CUDA_VERSION=12.9.1

#
# Docker builder stage.
#
FROM nvidia/cuda:${NVIDIA_CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS builder

ARG COLMAP_GIT_COMMIT="release/3.10"
ARG GLOMAP_GIT_COMMIT=main
ARG CUDA_ARCHITECTURES=native
ENV QT_XCB_GL_INTEGRATION=xcb_egl

# Prevent stop building ubuntu at time zone selection.
ENV DEBIAN_FRONTEND=noninteractive

# Prepare and empty machine for building.
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        git \
        cmake \
        ninja-build \
        build-essential \
        libboost-program-options-dev \
        libboost-filesystem-dev \
        libboost-graph-dev \
        libboost-system-dev \
        libeigen3-dev \
        libflann-dev \
        libfreeimage-dev \
        libmetis-dev \
        libgoogle-glog-dev \
        libgtest-dev \
        libsqlite3-dev \
        libglew-dev \
        qtbase5-dev \
        libqt5opengl5-dev \
        libcgal-dev \
        libsuitesparse-dev \
        libatlas-base-dev \
        cudss

# Build CERES from source with CUDA support
RUN git clone https://github.com/ceres-solver/ceres-solver.git
RUN cd ceres-solver && \
    git submodule update --init --recursive && \   
    mkdir build && \
    cd build && \
    cmake .. -DUSE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
        -DCMAKE_INSTALL_PREFIX=/colmap_installed -DCMAKE_BUILD_TYPE=Release && \
    make -j && \
    make install

# Build and install COLMAP.
RUN git clone https://github.com/colmap/colmap.git
RUN cd colmap && \
    git fetch https://github.com/colmap/colmap.git ${COLMAP_GIT_COMMIT} && \
    git checkout FETCH_HEAD && \
    mkdir build && \
    cd build && \
    cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
        -DCMAKE_INSTALL_PREFIX=/colmap_installed && \
    ninja install

# Build and install GLOMAP
COPY . /glomap
RUN mkdir glomap/build
RUN cd glomap/build && \
    cmake .. -GNinja -DCMAKE_INSTALL_PREFIX=/colmap_installed && \
    ninja install


#
# Docker runtime stage.
#
FROM nvidia/cuda:${NVIDIA_CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} AS runtime

# Minimal dependencies to run COLMAP binary compiled in the builder stage.
# Note: this reduces the size of the final image considerably, since all the
# build dependencies are not needed.
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        libboost-filesystem1.83.0 \
        libboost-program-options1.83.0 \
        libc6 \
        libfreeimage3 \
        libgcc-s1 \
        libgl1 \
        libglew2.2 \
        libgoogle-glog0v6 \
        libsuitesparse-dev \
        libatlas3-base \
        libqt5core5a \
        libqt5gui5 \
        libqt5widgets5 \
        libmetis5 \
        libopengl0 \
        cudss

# # Copy all files from /colmap_installed/ in the builder stage to /usr/local/ in
# # the runtime stage. This simulates installing COLMAP in the default location
# # (/usr/local/), which simplifies environment variables. It also allows the user
# # of this Docker image to use it as a base image for compiling against COLMAP as
# # a library. For instance, CMake will be able to find COLMAP easily with the
# # command: find_package(COLMAP REQUIRED).
COPY --from=builder /colmap_installed/ /usr/local/
COPY ./scripts/process-dataset.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/process-dataset.sh
