# rosbag_reading

`rosbag_reading` is a tool designed to simplify ROS bag data analysis and reduce the time required to review data in PlotJuggler.

Instead of manually loading bag files into PlotJuggler and checking the plots one by one, this tool reads the bag files directly and automatically generates the required analysis. It is useful for comparing multiple test runs and extracting key performance metrics such as maximum speed.

## Repository

```bash
git clone https://github.com/IlhamAkbar021/rosbag_reading.git
```

## Features

- Read and analyze ROS bag files directly
- Support loading up to **5 bag files** simultaneously
- Compare data from multiple test runs
- Automatically generate plots
- Extract key metrics without manual inspection
- Reduce analysis time compared to using PlotJuggler alone

## Usage

1. Clone the repository.
2. Run the application.
   ```bash
   rosbag_reading.py
   ```
4. Select the directory containing the bag files.
5. Load up to **3 bag files or 5 bags files** for analysis.
6. The tool will process the data and generate plots and analysis results automatically.

## Example Plot

The tool can generate plots similar to the example below:

<img width="1124" height="868" alt="Plot juggler" src="https://github.com/user-attachments/assets/70fec86f-6284-4c46-8757-5a82ae2780af" />

## Example Output

Users can directly obtain important information from the bag files, including:

- Maximum speed
- Speed trends
- Comparison between different test runs

This removes the need to manually inspect plots in PlotJuggler and helps make the analysis process faster and more efficient.

## Notes

- Maximum supported bag files per analysis: **5**
- All selected bag files should contain the required topics for analysis.
- The tool is intended to provide a quick overview and performance comparison of test results.

## Author

Ilham Akbar
